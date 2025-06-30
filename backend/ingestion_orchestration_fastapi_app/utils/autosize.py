# New file
import os
import logging

import psutil
import httpx

logger = logging.getLogger(__name__)


def autosize_batches(ml_url: str, reserve_ram_gb: int = 8) -> None:
    """Dynamically size *ML_INFERENCE_BATCH_SIZE* and *QDRANT_UPSERT_BATCH_SIZE* based on
    available system RAM **and** the GPU‐safe batch size reported by the ML inference service.

    The computed values are written to *os.environ* **only if** the caller has not already set
    the corresponding variables – this ensures explicit operator overrides always win.

    Parameters
    ----------
    ml_url : str
        Base URL of the ML inference service (e.g. ``http://localhost:8001``).
    reserve_ram_gb : int, optional
        Amount of RAM (in **GiB**) to leave untouched for the OS and other processes.
    """

    # ---------------------------------------------------------------------
    # 1️⃣  Query GPU-safe batch size from the ML service (may fail gracefully)
    # ---------------------------------------------------------------------
    safe_clip = 1  # conservative default
    try:
        resp = httpx.get(f"{ml_url}/api/v1/capabilities", timeout=10)
        resp.raise_for_status()
        safe_clip = int(resp.json().get("safe_clip_batch", 1))
        logger.info("[autosize] ML service reports safe GPU batch size: %s", safe_clip)
    except Exception as exc:  # pragma: no cover – network errors ignored
        logger.warning("[autosize] Could not fetch ML capabilities (%s) – falling back to 1", exc)

    # ---------------------------------------------------------------------
    # 2️⃣  Estimate host-RAM-limited batch sizes (leave generous safety margin)
    # ---------------------------------------------------------------------
    vm = psutil.virtual_memory()
    free_ram = max(vm.available - reserve_ram_gb * 1024**3, 512 * 1024**2)  # bytes, min 512 MiB

    # Heuristics: assume ~2 MiB per *encoded* image in-flight within the ingestion process and
    # ~6 KiB per point payload when upserting to Qdrant (vector + small JSON payload).
    ram_batch_images = int((free_ram * 0.60) / (2 * 1024 * 1024))  # 60 % of RAM budget
    ram_batch_qdrant = int((free_ram * 0.10) / (6 * 1024))        # 10 % of RAM budget

    ml_batch = max(1, min(safe_clip, ram_batch_images, 2048))      # hard-cap to 2048
    qdrant_batch = max(32, min(ram_batch_qdrant, 2048))

    # ---------------------------------------------------------------------
    # 3️⃣  Export env vars **only if** not already defined
    # ---------------------------------------------------------------------
    if "ML_INFERENCE_BATCH_SIZE" not in os.environ:
        os.environ["ML_INFERENCE_BATCH_SIZE"] = str(ml_batch)
        logger.info("[autosize] Set ML_INFERENCE_BATCH_SIZE=%s", ml_batch)
    else:
        logger.info("[autosize] ML_INFERENCE_BATCH_SIZE manually set to %s – keeping override", os.environ["ML_INFERENCE_BATCH_SIZE"])

    if "QDRANT_UPSERT_BATCH_SIZE" not in os.environ:
        os.environ["QDRANT_UPSERT_BATCH_SIZE"] = str(qdrant_batch)
        logger.info("[autosize] Set QDRANT_UPSERT_BATCH_SIZE=%s", qdrant_batch)
    else:
        logger.info("[autosize] QDRANT_UPSERT_BATCH_SIZE manually set to %s – keeping override", os.environ["QDRANT_UPSERT_BATCH_SIZE"])

    logger.info("[autosize] Effective batch sizes – ML:%s  Qdrant:%s", os.environ["ML_INFERENCE_BATCH_SIZE"], os.environ["QDRANT_UPSERT_BATCH_SIZE"]) 