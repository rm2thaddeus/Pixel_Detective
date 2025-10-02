import asyncio
import logging
import diskcache
from typing import Any
import os
import base64
import io

from qdrant_client.http.models import PointStruct

from .manager import JobContext
from . import utils
from . import image_processing

logger = logging.getLogger(__name__)

# The cache is a thread-safe and process-safe key-value store.
# We can use a single instance across all workers.
CACHE_DIR = ".diskcache"
cache = diskcache.Cache(CACHE_DIR)


async def process_files(ctx: JobContext, collection_name: str):
    """
    Consumes file paths from raw_queue, performs CPU-bound work, and pushes
    to the next queue (ml_queue or db_queue). Runs indefinitely until cancelled.
    """
    while True:
        try:
            file_path = await ctx.raw_queue.get()

            # Sentinel propagation for batching/shutdown
            if file_path is None:
                await ctx.ml_queue.put(None)
                ctx.raw_queue.task_done()
                break

            try:
                # --- CPU-bound work ---
                # Run synchronous file I/O and hashing in a separate thread
                # to avoid blocking the asyncio event loop.
                loop = asyncio.get_running_loop()
                file_hash = await loop.run_in_executor(None, utils.compute_sha256, file_path)

                # --- Cache Check ---
                cache_key = f"{collection_name}:{file_hash}"
                cached_data = cache.get(cache_key)

                if cached_data:
                    # Cache Hit: Send directly to DB
                    point = PointStruct(
                        id=cached_data["id"],
                        vector=cached_data["vector"],
                        payload=cached_data["payload"],
                    )
                    await ctx.db_queue.put(point)
                    ctx.cached_files += 1
                    ctx.add_log(f"Cache hit for {os.path.basename(file_path)}")
                else:
                    # Cache Miss: Decode image, then send to ML queue for processing
                    loop = asyncio.get_running_loop()
                    
                    # 1. Decode the image using our new processing utility
                    image_pil, error = await loop.run_in_executor(
                        None, image_processing.decode_and_prep_image, file_path
                    )

                    if error or image_pil is None:
                        ctx.add_log(f"Failed to decode {os.path.basename(file_path)}: {error}", level="error")
                        ctx.failed_files += 1
                        ctx.raw_queue.task_done()
                        continue

                    # 2. Serialize PIL image to base64 PNG for the ML service
                    img_byte_arr = io.BytesIO()
                    image_pil.save(img_byte_arr, format='PNG')
                    image_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

                    # 3. Create a smaller thumbnail from the PIL image for the frontend
                    thumbnail_pil = image_pil.copy()
                    thumbnail_pil.thumbnail((200, 200))
                    thumb_byte_arr = io.BytesIO()
                    thumbnail_pil.save(thumb_byte_arr, format='JPEG', quality=85)
                    thumbnail_base64 = base64.b64encode(thumb_byte_arr.getvalue()).decode('utf-8')
                    
                    # 4. Extract metadata
                    metadata = await loop.run_in_executor(None, utils.extract_image_metadata, file_path)

                    await ctx.ml_queue.put({
                        "unique_id": file_hash,
                        "file_hash": file_hash,
                        "image_base64": image_base64,
                        "thumbnail_base64": thumbnail_base64,
                        "filename": os.path.basename(file_path),
                        "metadata": metadata,
                        "collection_name": collection_name,
                    })
                    ctx.processed_files += 1

            except Exception as e:
                logger.error(f"[{ctx.job_id}] Failed to process file {file_path}: {e}", exc_info=True)
                ctx.failed_files += 1
            finally:
                # Always call task_done even if processing fails
                ctx.raw_queue.task_done()

        except asyncio.CancelledError:
            logger.info(f"[{ctx.job_id}] CPU worker cancelled.")
            break
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Unhandled error in CPU worker: {e}", exc_info=True)
            break
