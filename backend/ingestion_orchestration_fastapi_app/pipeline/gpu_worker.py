import asyncio
import logging
import httpx
import os
import uuid
import base64

from qdrant_client.http.models import PointStruct

from .manager import JobContext
from .cpu_processor import cache # Import the shared cache instance
from . import utils

logger = logging.getLogger(__name__)

ML_SERVICE_URL = os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
ML_BATCH_SIZE = int(os.environ.get("ML_INFERENCE_BATCH_SIZE", "32"))
REQUEST_TIMEOUT = int(os.environ.get("ML_REQUEST_TIMEOUT", "300"))

async def send_batch_to_ml_service(batch_items: list[dict]) -> list[dict]:
    """Sends a batch of items to the ML inference service."""
    if not batch_items:
        return []

    # Prepare request data
    images_payload = []
    for item in batch_items:
        images_payload.append({
            "unique_id": item["file_hash"],
            "image_base64": item["image_base64"],
            "filename": item["filename"],
        })

    if not images_payload:
        return []

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption",
                json={"images": images_payload},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json().get("results", [])
        except httpx.RequestError as e:
            logger.error(f"HTTP request to ML service failed: {e}")
            return [{"unique_id": item["unique_id"], "error": str(e)} for item in images_payload]
        except Exception as e:
            logger.error(f"An unexpected error occurred when calling ML service: {e}", exc_info=True)
            return [{"unique_id": item["unique_id"], "error": "Unknown error"} for item in images_payload]


async def process_ml_batches(ctx: JobContext):
    """
    Consumes items from ml_queue, batches them, sends them to the ML service,
    and places the results in the db_queue. Runs indefinitely until cancelled.
    """
    while True:
        try:
            # Gather a batch of items using the new utility function
            batch_items = await utils.gather_batch(
                ctx.ml_queue, 
                max_size=ML_BATCH_SIZE, 
                timeout=1.0
            )

            if not batch_items:
                continue

            # Send batch to ML service
            ml_results = await send_batch_to_ml_service(batch_items)

            # Create a map of file_hash -> original_item for easy lookup
            item_map = {item["file_hash"]: item for item in batch_items}

            for result in ml_results:
                file_hash = result.get("unique_id")
                original_item = item_map.get(file_hash)

                if not original_item:
                    logger.warning(f"[{ctx.job_id}] Received ML result for unknown hash: {file_hash}")
                    continue

                if result.get("error"):
                    ctx.failed_files += 1
                    ctx.add_log(f"ML service failed for {original_item['metadata']['filename']}: {result['error']}", level="error")
                else:
                    try:
                        # Prepare payload for Qdrant
                        payload = original_item["metadata"]
                        payload["caption"] = result.get("caption")
                        payload["thumbnail_base64"] = original_item.get("thumbnail_base64")
                        
                        point_id = str(uuid.uuid4())
                        point = PointStruct(
                            id=point_id,
                            vector=result["embedding"],
                            payload=payload
                        )
                        
                        await ctx.db_queue.put(point)

                        # Cache the successful result
                        cache_key = f"{original_item['collection_name']}:{file_hash}"
                        cache.set(cache_key, {
                            "id": point_id,
                            "vector": result["embedding"],
                            "payload": payload
                        })
                    except Exception as e:
                        logger.error(f"[{ctx.job_id}] Error processing ML result for {file_hash}: {e}", exc_info=True)
                        ctx.failed_files += 1
                
            # No need to call task_done here as gather_batch does it

        except asyncio.CancelledError:
            logger.info(f"[{ctx.job_id}] GPU worker cancelled.")
            break
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Unhandled error in GPU worker: {e}", exc_info=True)
            break
