import asyncio
import logging
import diskcache
from typing import Any
import os

from qdrant_client.http.models import PointStruct

from .manager import JobContext
from . import utils

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
                    # Cache Miss: Send to ML queue for processing
                    metadata = await loop.run_in_executor(None, utils.extract_image_metadata, file_path)
                    thumbnail = await loop.run_in_executor(None, utils.create_thumbnail_base64, file_path)
                    
                    if not thumbnail:
                         ctx.add_log(f"Could not generate thumbnail for {file_path}", level="warning")

                    await ctx.ml_queue.put({
                        "file_path": file_path,
                        "file_hash": file_hash,
                        "metadata": metadata,
                        "thumbnail_base64": thumbnail,
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
