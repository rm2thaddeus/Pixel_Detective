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
POLL_INTERVAL = float(os.environ.get("ML_POLL_INTERVAL", "1.0"))

async def send_batch_to_ml_service(batch_items: list[dict]) -> list[dict]:
    """Submit a batch to the ML service and poll until results are ready."""
    if not batch_items:
        return []

    images_payload = [
        {
            "unique_id": item["file_hash"],
            "image_base64": item["image_base64"],
            "filename": item["filename"],
        }
        for item in batch_items
    ]

    async with httpx.AsyncClient() as client:
        try:
            submit_resp = await client.post(
                f"{ML_SERVICE_URL}/api/v1/batch_embed_and_caption",
                json={"images": images_payload},
                timeout=REQUEST_TIMEOUT,
            )
            submit_resp.raise_for_status()
            submit_data = submit_resp.json()

            # Legacy behaviour: immediate results
            if "results" in submit_data:
                return submit_data.get("results", [])

            job_id = submit_data.get("job_id")
            if not job_id:
                logger.error("ML service response missing job_id")
                return [
                    {"unique_id": item["unique_id"], "error": "No job_id returned"}
                    for item in images_payload
                ]

            results_map: dict[str, dict] = {}
            start = asyncio.get_event_loop().time()

            while True:
                try:
                    status_resp = await client.get(
                        f"{ML_SERVICE_URL}/status/{job_id}", timeout=REQUEST_TIMEOUT
                    )
                    status_resp.raise_for_status()
                    status_data = status_resp.json()
                except Exception as poll_error:
                    logger.error(
                        f"Error polling ML job {job_id}: {poll_error}", exc_info=True
                    )
                    if asyncio.get_event_loop().time() - start > REQUEST_TIMEOUT:
                        break
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                for res in status_data.get("results", []):
                    uid = res.get("unique_id")
                    if uid:
                        results_map[uid] = res

                if status_data.get("status") in {"completed", "failed"}:
                    break
                if len(results_map) == len(images_payload):
                    break
                if asyncio.get_event_loop().time() - start > REQUEST_TIMEOUT:
                    logger.warning(
                        f"Timeout waiting for ML job {job_id}, returning partial results"
                    )
                    break

                await asyncio.sleep(POLL_INTERVAL)

            # Assemble results in original order with fallbacks for missing items
            final_results: list[dict] = []
            for item in images_payload:
                uid = item["unique_id"]
                if uid in results_map:
                    final_results.append(results_map[uid])
                else:
                    final_results.append({"unique_id": uid, "error": "No result"})
            return final_results

        except Exception as e:
            logger.error(
                f"An unexpected error occurred when calling ML service: {e}",
                exc_info=True,
            )
            return [
                {"unique_id": item["unique_id"], "error": str(e)}
                for item in images_payload
            ]


async def process_ml_batches(ctx: JobContext):
    """
    Consumes items from ml_queue, batches them, sends them to the ML service,
    and places the results in the db_queue. Runs until all CPU workers are done.
    Implements smart batch flushing: first batch flushes after 30s if not full, then always flushes as soon as possible.
    """
    batch = []
    sentinels_received = 0
    first_batch = True
    first_batch_start = None
    while True:
        try:
            if first_batch:
                # For the first batch, wait up to 30s for items to fill the batch
                if first_batch_start is None:
                    first_batch_start = asyncio.get_event_loop().time()
                timeout = 30.0 - (asyncio.get_event_loop().time() - first_batch_start)
                if timeout <= 0:
                    timeout = 0.01
                try:
                    item = await asyncio.wait_for(ctx.ml_queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    # Timeout: flush whatever is in the batch
                    if batch:
                        logger.info(f"[{ctx.job_id}] [ML] Flushing first batch early after 30s: {len(batch)} items")
                        await _flush_ml_batch(ctx, batch)
                        batch = []
                        first_batch = False
                        first_batch_start = None
                    continue
                if item is None:
                    sentinels_received += 1
                    ctx.ml_queue.task_done()
                    # Only exit after all CPU workers have sent their sentinel
                    if sentinels_received == ctx.cpu_worker_count:
                        if batch:
                            logger.info(f"[{ctx.job_id}] [ML] Flushing final ML batch of size {len(batch)} (first batch mode)")
                            await _flush_ml_batch(ctx, batch)
                        for _ in range(ctx.db_worker_count):
                            await ctx.db_queue.put(None)
                        break
                    else:
                        continue
                batch.append(item)
                if len(batch) >= ctx.ml_batch_size:
                    logger.info(f"[{ctx.job_id}] [ML] Sending first full ML batch of size {len(batch)}")
                    await _flush_ml_batch(ctx, batch)
                    batch = []
                    first_batch = False
                    first_batch_start = None
                ctx.ml_queue.task_done()
            else:
                # After first batch, always flush as soon as batch is full, or if queue is empty for a short time
                try:
                    item = await asyncio.wait_for(ctx.ml_queue.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    # Timeout: flush whatever is in the batch
                    if batch:
                        logger.info(f"[{ctx.job_id}] [ML] Flushing partial ML batch after idle: {len(batch)} items")
                        await _flush_ml_batch(ctx, batch)
                        batch = []
                    continue
                if item is None:
                    sentinels_received += 1
                    ctx.ml_queue.task_done()
                    if sentinels_received == ctx.cpu_worker_count:
                        if batch:
                            logger.info(f"[{ctx.job_id}] [ML] Flushing final ML batch of size {len(batch)}")
                            await _flush_ml_batch(ctx, batch)
                        for _ in range(ctx.db_worker_count):
                            await ctx.db_queue.put(None)
                        break
                    else:
                        continue
                batch.append(item)
                if len(batch) >= ctx.ml_batch_size:
                    logger.info(f"[{ctx.job_id}] [ML] Sending ML batch of size {len(batch)}")
                    await _flush_ml_batch(ctx, batch)
                    batch = []
                ctx.ml_queue.task_done()
        except asyncio.CancelledError:
            logger.info(f"[{ctx.job_id}] GPU worker cancelled.")
            break
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Unhandled error in GPU worker: {e}", exc_info=True)
            break

async def _flush_ml_batch(ctx: JobContext, batch: list):
    if not batch:
        return
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
