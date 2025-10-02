import os
import logging
import psutil
import httpx

CAPABILITIES_FETCHED = False

async def autosize_batches(ml_url: str) -> None:
    """Compute batch sizes based on ML service capability and system RAM."""
    log = logging.getLogger(__name__)
    safe_blip = None
    safe_clip = None
    safe_batch = None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{ml_url}/api/v1/capabilities")
            r.raise_for_status()
            caps = r.json()
            safe_blip = caps.get("SAFE_BLIP_BATCH_SIZE") or caps.get("safe_blip_batch")
            safe_clip = caps.get("SAFE_CLIP_BATCH_SIZE") or caps.get("safe_clip_batch")
            safe_batch = caps.get("safe_batch_size") or caps.get("safe_batch")
            if safe_blip is not None:
                safe_blip = int(safe_blip)
            if safe_clip is not None:
                safe_clip = int(safe_clip)
            if safe_batch is not None:
                safe_batch = int(safe_batch)
    except Exception as e:
        log.warning(f"Could not fetch ML capabilities, defaulting to 1: {e}")

    free_ram = psutil.virtual_memory().available
    ram_batch = int((free_ram * 0.60) / (2 * 1024 * 1024))
    ram_upsert = int((free_ram * 0.10) / (6 * 1024))

    # Priority: BLIP > CLIP > safe_batch > 1
    if safe_blip is not None:
        ml_batch = safe_blip
    elif safe_clip is not None:
        ml_batch = safe_clip
    elif safe_batch is not None:
        ml_batch = safe_batch
    else:
        # 🛟 Graceful fallback – retain last known good value instead of 1
        prev_val = os.environ.get("ML_INFERENCE_BATCH_SIZE")
        if prev_val and prev_val.isdigit() and int(prev_val) > 1:
            ml_batch = int(prev_val)
            log.warning(
                "Could not fetch ML capabilities – falling back to previous ML_INFERENCE_BATCH_SIZE=%s",
                ml_batch,
            )
        else:
            ml_batch = 1
    ml_batch = max(1, min(ml_batch, ram_batch, 2048))
    qdrant_batch = max(32, min(ram_upsert, 2048))

    os.environ["ML_INFERENCE_BATCH_SIZE"] = str(ml_batch)
    os.environ["QDRANT_UPSERT_BATCH_SIZE"] = str(qdrant_batch)
    log.info(
        "Auto-set ML_INFERENCE_BATCH_SIZE=%s, QDRANT_UPSERT_BATCH_SIZE=%s",
        ml_batch,
        qdrant_batch,
    )
    global CAPABILITIES_FETCHED
    CAPABILITIES_FETCHED = True
