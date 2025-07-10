import asyncio
import logging
import os
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

from .manager import JobContext
from . import utils

logger = logging.getLogger(__name__)

QDRANT_BATCH_SIZE = int(os.environ.get("QDRANT_UPSERT_BATCH_SIZE", "64"))

async def upsert_to_db(
    ctx: JobContext,
    collection_name: str,
    qdrant_client: QdrantClient
):
    """
    Consumes points from db_queue, batches them, and upserts them to Qdrant.
    Runs until sentinel is received.
    """
    batch_points = []
    while True:
        try:
            point = await ctx.db_queue.get()
            if point is None:
                # Upsert any remaining points in the batch
                if batch_points:
                    try:
                        qdrant_client.upsert(
                            collection_name=collection_name,
                            points=batch_points,
                            wait=False
                        )
                        ctx.add_log(f"Upserted {len(batch_points)} points to Qdrant.")
                    except Exception as e:
                        logger.error(f"[{ctx.job_id}] Failed to upsert batch to Qdrant: {e}", exc_info=True)
                        ctx.failed_files += len(batch_points)
                        ctx.add_log(f"Failed to upsert {len(batch_points)} points: {e}", level="error")
                ctx.db_queue.task_done()
                break
            batch_points.append(point)
            if len(batch_points) >= ctx.qdrant_batch_size:
                try:
                    qdrant_client.upsert(
                        collection_name=collection_name,
                        points=batch_points,
                        wait=False
                    )
                    ctx.add_log(f"Upserted {len(batch_points)} points to Qdrant.")
                except Exception as e:
                    logger.error(f"[{ctx.job_id}] Failed to upsert batch to Qdrant: {e}", exc_info=True)
                    ctx.failed_files += len(batch_points)
                    ctx.add_log(f"Failed to upsert {len(batch_points)} points: {e}", level="error")
                batch_points = []
            ctx.db_queue.task_done()
        except asyncio.CancelledError:
            logger.info(f"[{ctx.job_id}] DB Upserter worker cancelled.")
            break
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Unhandled error in DB Upserter worker: {e}", exc_info=True)
            break
