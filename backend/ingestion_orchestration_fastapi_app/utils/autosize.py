import os
import logging
import psutil
import httpx

CAPABILITIES_FETCHED = False

async def autosize_batches(ml_url: str) -> None:
    """Compute batch sizes based on ML service capability and system RAM."""
    log = logging.getLogger(__name__)
    safe_clip = 1
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{ml_url}/api/v1/capabilities")
            r.raise_for_status()
            safe_clip = int(r.json().get("safe_clip_batch", 1))
    except Exception as e:
        log.warning(f"Could not fetch ML capabilities, defaulting to 1: {e}")

    free_ram = psutil.virtual_memory().available
    ram_batch = int((free_ram * 0.60) / (2 * 1024 * 1024))
    ram_upsert = int((free_ram * 0.10) / (6 * 1024))

    ml_batch = max(1, min(safe_clip, ram_batch, 2048))
    qdrant_batch = max(32, min(ram_upsert, 2048))

    os.environ.setdefault("ML_INFERENCE_BATCH_SIZE", str(ml_batch))
    os.environ.setdefault("QDRANT_UPSERT_BATCH_SIZE", str(qdrant_batch))
    log.info(
        "Auto-set ML_INFERENCE_BATCH_SIZE=%s, QDRANT_UPSERT_BATCH_SIZE=%s",
        ml_batch,
        qdrant_batch,
    )
    global CAPABILITIES_FETCHED
    CAPABILITIES_FETCHED = True
