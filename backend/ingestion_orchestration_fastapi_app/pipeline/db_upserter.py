import asyncio
import logging
import os
from typing import List
import json

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, Filter, FieldCondition

from .manager import JobContext
from . import utils
from .cpu_processor import cache  # Import the shared cache instance

logger = logging.getLogger(__name__)

QDRANT_BATCH_SIZE = int(os.environ.get("QDRANT_UPSERT_BATCH_SIZE", "64"))

MAX_QDRANT_PAYLOAD = 8 * 1024 * 1024  # 8MB safety margin
MAX_BATCH_SIZE = 10  # Tune as needed

async def upsert_to_db(
    ctx: JobContext,
    collection_name: str,
    qdrant_client: QdrantClient
):
    """
    Consumes points from db_queue, upserts them to Qdrant in small batches as soon as they arrive.
    Implements split and retry logic for oversized batches, and at the end, checks the cache for any records not yet upserted.
    """
    batch_points = []
    batch_bytes = 0
    upserted_ids = set()

    def estimate_batch_size(points):
        return len(json.dumps([p.dict() for p in points]).encode("utf-8"))

    async def check_point_exists(point_id: str) -> bool:
        """Check if a point with the given ID already exists in Qdrant."""
        try:
            result = qdrant_client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
                with_vectors=False,
                with_payload=False
            )
            return len(result) > 0
        except Exception as e:
            # If retrieve fails, assume point doesn't exist
            logger.debug(f"[{ctx.job_id}] Error checking point existence for {point_id}: {e}")
            return False

    async def upsert_batch(points):
        if not points:
            return
        
        # Filter out points that already exist in the database
        points_to_upsert = []
        for point in points:
            point_id = str(point.id)
            if point_id in upserted_ids:
                logger.debug(f"[{ctx.job_id}] Point {point_id} already upserted in this session, skipping")
                continue
            
            if await check_point_exists(point_id):
                logger.info(f"[{ctx.job_id}] Point {point_id} already exists in database, skipping")
                upserted_ids.add(point_id)
                continue
            
            points_to_upsert.append(point)
        
        if not points_to_upsert:
            logger.debug(f"[{ctx.job_id}] All points in batch already exist, skipping upsert")
            return
        
        try:
            # Estimate payload size
            payload_size = estimate_batch_size(points_to_upsert)
            if payload_size > MAX_QDRANT_PAYLOAD and len(points_to_upsert) > 1:
                # Split and retry
                mid = len(points_to_upsert) // 2
                await upsert_batch(points_to_upsert[:mid])
                await upsert_batch(points_to_upsert[mid:])
                return
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points_to_upsert,
                wait=False
            )
            for p in points_to_upsert:
                upserted_ids.add(str(p.id))
            ctx.add_log(f"Upserted {len(points_to_upsert)} points to Qdrant.")
            logger.info(f"[{ctx.job_id}] Upserted {len(points_to_upsert)} points to Qdrant.")
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Failed to upsert batch to Qdrant: {e}", exc_info=True)
            ctx.failed_files += len(points_to_upsert)
            ctx.add_log(f"Failed to upsert {len(points_to_upsert)} points: {e}", level="error")
            # Optionally, retry one-by-one if batch fails
            if len(points_to_upsert) > 1:
                for p in points_to_upsert:
                    await upsert_batch([p])

    while True:
        try:
            try:
                point = await asyncio.wait_for(ctx.db_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No item received, just flush batch and continue (do NOT call task_done)
                if batch_points:
                    await upsert_batch(batch_points)
                    batch_points = []
                    batch_bytes = 0
                continue

            if point is None:
                # Sentinel received, flush and exit
                if batch_points:
                    await upsert_batch(batch_points)
                    batch_points = []
                    batch_bytes = 0
                ctx.db_queue.task_done()  # Only call for actual get()
                break

            # Estimate size of this point
            point_bytes = estimate_batch_size([point])
            if batch_points and (batch_bytes + point_bytes > MAX_QDRANT_PAYLOAD or len(batch_points) >= MAX_BATCH_SIZE):
                await upsert_batch(batch_points)
                batch_points = []
                batch_bytes = 0
            batch_points.append(point)
            batch_bytes += point_bytes
            ctx.db_queue.task_done()
        except asyncio.CancelledError:
            logger.info(f"[{ctx.job_id}] DB Upserter worker cancelled.")
            break
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Unhandled error in DB Upserter worker: {e}", exc_info=True)
            break

    # Final flush
    if batch_points:
        await upsert_batch(batch_points)

    # --- Cache scan for missed records ---
    logger.info(f"[{ctx.job_id}] Scanning cache for missed records to upsert...")
    prefix = f"{collection_name}:"
    for key in cache.iterkeys(prefix=prefix):
        try:
            cached = cache.get(key)
            if not cached:
                continue
            point_id = str(cached["id"])
            if point_id in upserted_ids:
                continue  # Already upserted
            point = PointStruct(
                id=point_id,
                vector=cached["vector"],
                payload=cached["payload"]
            )
            await upsert_batch([point])
            logger.info(f"[{ctx.job_id}] Upserted missed cached record {point_id}")
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Error upserting cached record {key}: {e}", exc_info=True)
