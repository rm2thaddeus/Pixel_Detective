import asyncio
import uuid
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Coroutine, Optional
from dataclasses import dataclass, field
import logging
import os
import httpx

from fastapi import BackgroundTasks
from qdrant_client import QdrantClient

# Logger setup
logger = logging.getLogger(__name__)

# Job status enumeration
class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class JobContext:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # --- Configurable pipeline parameters ---
    ml_batch_size: int = 32
    qdrant_batch_size: int = 64
    cpu_worker_count: int = 2
    ml_worker_count: int = 1
    db_worker_count: int = 1
    # --- New: Model-specific batch sizes ---
    clip_batch_size: Optional[int] = None
    blip_batch_size: Optional[int] = None
    
    # --- Queues for pipeline stages ---
    raw_queue: asyncio.Queue = field(init=False)
    ml_queue: asyncio.Queue = field(init=False)
    db_queue: asyncio.Queue = field(init=False)
    
    # --- Progress tracking ---
    total_files: int = 0
    processed_files: int = 0
    cached_files: int = 0
    failed_files: int = 0
    
    logs: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[asyncio.Task] = field(default_factory=list)
    
    def __post_init__(self):
        self.raw_queue = asyncio.Queue(maxsize=self.ml_batch_size * 2)
        self.ml_queue = asyncio.Queue(maxsize=self.ml_batch_size * 2)
        self.db_queue = asyncio.Queue(maxsize=self.qdrant_batch_size * 2)
    
    @property
    def progress(self) -> float:
        if self.total_files == 0:
            return 0.0
        # Ensure we don't go over 100%
        processed = self.cached_files + self.processed_files
        return min(100.0, (processed / self.total_files) * 100)
        
    def add_log(self, message: str, level: str = "info"):
        self.logs.append({"timestamp": datetime.utcnow().isoformat(), "level": level, "message": message})

# In-memory store for active jobs.
active_jobs: Dict[str, JobContext] = {}

# Local pipeline stages
from . import io_scanner, cpu_processor, gpu_worker, db_upserter

async def _run_pipeline(
    job_id: str,
    directory_path: str,
    collection_name: str,
    qdrant_client: QdrantClient
):
    """The main coroutine that sets up and runs the pipeline stages using queue.join() for flow control."""
    ctx = active_jobs.get(job_id)
    if not ctx:
        logger.error(f"Job {job_id} context not found.")
        return

    ctx.status = JobStatus.RUNNING
    ctx.add_log(f"Starting pipeline for directory: {directory_path}")

    # Log queue and worker configuration
    logger.info(f"[Pipeline Config] ml_batch_size={ctx.ml_batch_size}, qdrant_batch_size={ctx.qdrant_batch_size}, "
                f"raw_queue.maxsize={ctx.raw_queue.maxsize}, ml_queue.maxsize={ctx.ml_queue.maxsize}, db_queue.maxsize={ctx.db_queue.maxsize}, "
                f"cpu_worker_count={ctx.cpu_worker_count}, ml_worker_count={ctx.ml_worker_count}, db_worker_count={ctx.db_worker_count}")

    try:
        # --- Define and start all workers ---
        scanner_task = asyncio.create_task(io_scanner.scan_directory(ctx, directory_path))
        
        cpu_workers = [
            cpu_processor.process_files(ctx, collection_name)
            for _ in range(ctx.cpu_worker_count)
        ]
        
        gpu_workers = [
            gpu_worker.process_ml_batches(ctx)
            for _ in range(ctx.ml_worker_count)
        ]
        
        db_upserters = [
            db_upserter.upsert_to_db(ctx, collection_name, qdrant_client)
            for _ in range(ctx.db_worker_count)
        ]
        
        all_workers = cpu_workers + gpu_workers + db_upserters
        ctx.tasks = [asyncio.create_task(worker) for worker in all_workers]

        # --- Orchestrate the pipeline flow ---
        await scanner_task # 1. Wait for the directory scan to complete
        ctx.add_log(f"Scan finished. Found {ctx.total_files} files.")
        
        await ctx.raw_queue.join() # 2. Wait for all files to be processed by CPU workers
        ctx.add_log("CPU processing stage complete.")
        
        await ctx.ml_queue.join() # 3. Wait for all ML batches to be processed by GPU workers
        ctx.add_log("ML inference stage complete.")
        
        await ctx.db_queue.join() # 4. Wait for all points to be upserted to the database
        ctx.add_log("Database upsert stage complete.")

        ctx.status = JobStatus.COMPLETED
        ctx.add_log("Pipeline completed successfully.")
        
    except Exception as e:
        logger.error(f"Pipeline for job {job_id} failed: {e}", exc_info=True)
        ctx.status = JobStatus.FAILED
        ctx.add_log(f"Pipeline failed: {str(e)}", level="error")
    finally:
        # --- Cleanup ---
        # Cancel all worker tasks to ensure they exit their while True loops
        for task in ctx.tasks:
            if not task.done():
                task.cancel()
        # Wait for tasks to acknowledge cancellation
        await asyncio.gather(*ctx.tasks, return_exceptions=True)
        
        ctx.end_time = time.time()
        logger.info(f"[{ctx.job_id}] Pipeline finished with status: {ctx.status.value}")


# Add a function to get ML service capabilities
def get_ml_service_capabilities(ml_service_url: str) -> dict:
    try:
        resp = httpx.get(f"{ml_service_url}/api/v1/capabilities", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Could not fetch ML service capabilities: {e}")
        return {}

def get_ingestion_service_capabilities(ingestion_service_url: str) -> dict:
    try:
        resp = httpx.get(f"{ingestion_service_url}/api/v1/capabilities", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Could not fetch ingestion service capabilities: {e}")
        return {}

# --- ML Capabilities Cache and Robust Fetch Logic ---
_ml_capabilities_cache = None
_ml_capabilities_last_fetch = 0
ML_CAPABILITIES_TTL = 60  # seconds

def fetch_ml_service_capabilities(ml_service_url: str, retries: int = 3) -> dict:
    """Fetch ML service capabilities with retries and cache the result."""
    global _ml_capabilities_cache, _ml_capabilities_last_fetch
    for attempt in range(retries):
        try:
            resp = httpx.get(f"{ml_service_url}/api/v1/capabilities", timeout=10)
            resp.raise_for_status()
            caps = resp.json()
            _ml_capabilities_cache = caps
            _ml_capabilities_last_fetch = time.time()
            return caps
        except Exception as e:
            logger.warning(f"Attempt {attempt+1}: Could not fetch ML service capabilities: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
    # Fallback to cache if available
    if _ml_capabilities_cache:
        logger.info("Using cached ML capabilities")
        return _ml_capabilities_cache
    # Final fallback
    logger.warning("No ML capabilities available, defaulting to safe values")
    return {"safe_batch_size": 1}

def get_latest_ml_capabilities(ml_service_url: str) -> dict:
    """Return cached ML capabilities if recent, else fetch new."""
    if _ml_capabilities_cache and (time.time() - _ml_capabilities_last_fetch < ML_CAPABILITIES_TTL):
        return _ml_capabilities_cache
    return fetch_ml_service_capabilities(ml_service_url)

async def start_pipeline(
    directory_path: str,
    collection_name: str,
    background_tasks: BackgroundTasks,
    qdrant_client: QdrantClient,
) -> str:
    # Dynamically determine ML batch size and queue size from ML service capabilities
    ML_SERVICE_URL = os.environ.get("ML_INFERENCE_SERVICE_URL", "http://localhost:8001")
    ml_caps = get_latest_ml_capabilities(ML_SERVICE_URL)
    logger.info(f"[Batch Size Negotiation] ML service capabilities: {ml_caps}")
    safe_clip_batch_size = ml_caps.get("safe_clip_batch")  # <-- fixed key
    safe_blip_batch_size = ml_caps.get("safe_blip_batch")  # <-- fixed key
    safe_ml_batch_size = ml_caps.get("safe_batch_size")    # <-- fallback for legacy

    # Prefer model-specific batch sizes, fallback to generic
    clip_batch_size = int(safe_clip_batch_size) if safe_clip_batch_size else (int(safe_ml_batch_size) if safe_ml_batch_size else 32)
    blip_batch_size = int(safe_blip_batch_size) if safe_blip_batch_size else (int(safe_ml_batch_size) if safe_ml_batch_size else 32)

    # Use BLIP batch size for ML operations (since we're doing captioning)
    ml_batch_size = blip_batch_size
    ml_queue_maxsize = ml_batch_size * 2

    # Log the batch size selection for debugging
    logger.info(f"[Batch Size Selection] ML capabilities: {ml_caps}")
    logger.info(f"[Batch Size Selection] CLIP batch size: {clip_batch_size}, BLIP batch size: {blip_batch_size}")
    logger.info(f"[Batch Size Selection] Using ML batch size: {ml_batch_size} (BLIP-based)")

    # Set Qdrant batch size and queue size from environment or fallback
    qdrant_batch_size = int(os.environ.get("QDRANT_UPSERT_BATCH_SIZE", 64))
    db_queue_maxsize = qdrant_batch_size * 2

    # Compute worker counts based on batch sizes
    cpu_worker_count = max(2, ml_batch_size // 32)
    ml_worker_count = 1
    db_worker_count = 1

    # Update environment variables for consistency
    os.environ["ML_INFERENCE_BATCH_SIZE"] = str(ml_batch_size)
    os.environ["QDRANT_UPSERT_BATCH_SIZE"] = str(qdrant_batch_size)

    ctx = JobContext(
        job_id=str(uuid.uuid4()),
        ml_batch_size=ml_batch_size,
        qdrant_batch_size=qdrant_batch_size,
        cpu_worker_count=cpu_worker_count,
        ml_worker_count=ml_worker_count,
        db_worker_count=db_worker_count,
        clip_batch_size=clip_batch_size,
        blip_batch_size=blip_batch_size,
    )
    # Override queue maxsize for ML and DB queues
    ctx.raw_queue = asyncio.Queue(maxsize=ml_queue_maxsize)
    ctx.ml_queue = asyncio.Queue(maxsize=ml_queue_maxsize)
    ctx.db_queue = asyncio.Queue(maxsize=db_queue_maxsize)

    active_jobs[ctx.job_id] = ctx

    background_tasks.add_task(
        _run_pipeline,
        ctx.job_id,
        directory_path,
        collection_name,
        qdrant_client
    )

    logger.info(f"Scheduled pipeline job {ctx.job_id} for collection '{collection_name}' (ml_batch_size={ml_batch_size}, ml_queue_maxsize={ml_queue_maxsize}, qdrant_batch_size={qdrant_batch_size}, db_queue_maxsize={db_queue_maxsize}, clip_batch_size={clip_batch_size}, blip_batch_size={blip_batch_size}, cpu_worker_count={cpu_worker_count}, ml_worker_count={ml_worker_count}, db_worker_count={db_worker_count})")
    return ctx.job_id

def get_job_status(job_id: str) -> Optional[JobContext]:
    return active_jobs.get(job_id)

def get_recent_jobs() -> List[Dict[str, Any]]:
    sorted_jobs = sorted(active_jobs.values(), key=lambda j: j.start_time, reverse=True)
    return [
        {
            "job_id": job.job_id,
            "status": job.status.value,
            "start_time": datetime.fromtimestamp(job.start_time).isoformat(),
            "progress": job.progress,
            "total_files": job.total_files,
            "processed_files": job.cached_files + job.processed_files,
            "failed_files": job.failed_files,
        }
        for job in sorted_jobs[:20]
    ]
