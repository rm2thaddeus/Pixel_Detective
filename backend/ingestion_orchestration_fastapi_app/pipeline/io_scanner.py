import asyncio
import os
import logging
from typing import Any

from .manager import JobContext

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff",
    ".dng", ".cr2", ".nef", ".arw", ".rw2", ".orf"
}

async def scan_directory(ctx: JobContext, directory_path: str):
    """
    Scans a directory for image files and puts their paths into the raw_queue.
    This coroutine finishes when the entire directory has been scanned.
    """
    logger.info(f"[{ctx.job_id}] Starting directory scan: {directory_path}")
    
    try:
        file_count = 0
        for root, _, files in os.walk(directory_path):
            for filename in files:
                if os.path.splitext(filename)[1].lower() in SUPPORTED_EXTENSIONS:
                    file_path = os.path.join(root, filename)
                    await ctx.raw_queue.put(file_path)
                    file_count += 1
            # Give other tasks a chance to run during a large directory scan
            await asyncio.sleep(0)

        ctx.total_files = file_count
        # Send sentinel (None) for each CPU worker to signal end-of-stream
        for _ in range(ctx.cpu_worker_count):
            await ctx.raw_queue.put(None)
        # This log is now in the manager after this task completes.
        
    except Exception as e:
        logger.error(f"[{ctx.job_id}] Error during directory scan: {e}", exc_info=True)
        ctx.add_log(f"Error during directory scan: {e}", level="error")
    
    logger.info(f"[{ctx.job_id}] IO Scanner finished.")
