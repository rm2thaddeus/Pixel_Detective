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
# Remove ML_BATCH_SIZE global, always use ctx.ml_batch_size
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
    and places the results in the db_queue. Runs until all CPU workers are done.
    Implements smart batch flushing: at pipeline start, if a full batch is not reached within 30s, flush whatever is available.
    After the first batch, flush as soon as a batch is full, or after 3s of waiting for more items.
    """
    batch = []
    sentinels_received = 0
    first_batch = True
    first_batch_start = None
    while True:
        try:
            # For the first batch, use a long timeout (30s), then switch to short (3s)
            batch_timeout = 30.0 if first_batch else 3.0
            # If batch is empty, block with timeout for the first item
            if not batch:
                try:
                    first_batch_start = first_batch_start or asyncio.get_event_loop().time()
                    item = await asyncio.wait_for(ctx.ml_queue.get(), timeout=batch_timeout)
                    batch.append(item)
                    ctx.ml_queue.task_done()
                except asyncio.TimeoutError:
                    # If nothing arrives in timeout, and batch is empty, just continue
                    continue
            # Try to fill the batch up to ml_batch_size, but don't block
            while len(batch) < ctx.ml_batch_size:
                try:
                    item = ctx.ml_queue.get_nowait()
                    batch.append(item)
                    ctx.ml_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            # If batch is full, or if we've waited long enough for the first batch, or if we've waited 3s for subsequent batches, flush
            should_flush = False
            if len(batch) >= ctx.ml_batch_size:
                should_flush = True
            elif first_batch and first_batch_start and (asyncio.get_event_loop().time() - first_batch_start >= 30.0):
                should_flush = True
            elif not first_batch and batch and len(batch) > 0:
                # For subsequent batches, flush if we've waited 3s since last item
                should_flush = True
            if should_flush:
                logger.info(f"[{ctx.job_id}] Sending ML batch of size {len(batch)}: {[i['file_hash'] for i in batch]}")
                ml_results = await send_batch_to_ml_service(batch)
                item_map = {i["file_hash"]: i for i in batch}
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
                            cache_key = f"{original_item['collection_name']}:{file_hash}"
                            cache.set(cache_key, {
                                "id": point_id,
                                "vector": result["embedding"],
                                "payload": payload
                            })
                        except Exception as e:
                            logger.error(f"[{ctx.job_id}] Error processing ML result for {file_hash}: {e}", exc_info=True)
                            ctx.failed_files += 1
                batch = []
                if first_batch:
                    first_batch = False
                    first_batch_start = None
            # Check for sentinels (end of stream)
            # If a sentinel is in the queue, process it
            while True:
                try:
                    item = ctx.ml_queue.get_nowait()
                    if item is None:
                        sentinels_received += 1
                        if sentinels_received == ctx.cpu_worker_count:
                            # Flush any remaining items
                            if batch:
                                logger.info(f"[{ctx.job_id}] Flushing final ML batch of size {len(batch)}: {[i['file_hash'] for i in batch]}")
                                ml_results = await send_batch_to_ml_service(batch)
                                item_map = {i["file_hash"]: i for i in batch}
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
                                            cache_key = f"{original_item['collection_name']}:{file_hash}"
                                            cache.set(cache_key, {
                                                "id": point_id,
                                                "vector": result["embedding"],
                                                "payload": payload
                                            })
                                        except Exception as e:
                                            logger.error(f"[{ctx.job_id}] Error processing ML result for {file_hash}: {e}", exc_info=True)
                                            ctx.failed_files += 1
                                batch = []
                            # Propagate sentinels downstream for all DB upserter workers
                            for _ in range(ctx.db_worker_count):
                                await ctx.db_queue.put(None)
                            ctx.ml_queue.task_done()
                            return
                        else:
                            ctx.ml_queue.task_done()
                            continue
                    else:
                        batch.append(item)
                        ctx.ml_queue.task_done()
                except asyncio.QueueEmpty:
                    break
        except asyncio.CancelledError:
            logger.info(f"[{ctx.job_id}] GPU worker cancelled.")
            break
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Unhandled error in GPU worker: {e}", exc_info=True)
            break
