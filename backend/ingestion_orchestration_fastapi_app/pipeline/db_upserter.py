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
    Runs indefinitely until cancelled.
    """
    while True:
        try:
            batch_points: List[PointStruct] = await utils.gather_batch(
                ctx.db_queue,
                max_size=QDRANT_BATCH_SIZE,
                timeout=1.0
            )

            if not batch_points:
                continue

            try:
                qdrant_client.upsert(
                    collection_name=collection_name,
                    points=batch_points,
                    wait=False # Set to False for async-like behavior
                )
                ctx.add_log(f"Upserted {len(batch_points)} points to Qdrant.")
            except Exception as e:
                logger.error(f"[{ctx.job_id}] Failed to upsert batch to Qdrant: {e}", exc_info=True)
                # Increment failed count for each item in the failed batch
                ctx.failed_files += len(batch_points)
                ctx.add_log(f"Failed to upsert {len(batch_points)} points: {e}", level="error")
            # No need to call task_done here as gather_batch does it
        
        except asyncio.CancelledError:
            logger.info(f"[{ctx.job_id}] DB Upserter worker cancelled.")
            break
        except Exception as e:
            logger.error(f"[{ctx.job_id}] Unhandled error in DB Upserter worker: {e}", exc_info=True)
            break
