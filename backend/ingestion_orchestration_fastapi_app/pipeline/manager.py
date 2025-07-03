import asyncio
import uuid
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Coroutine
from dataclasses import dataclass, field
import logging

from fastapi import BackgroundTasks
from qdrant_client import QdrantClient

# Local pipeline stages
from . import io_scanner, cpu_processor, gpu_worker, db_upserter

logger = logging.getLogger(__name__)

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
    end_time: float | None = None
    
    # --- Queues for pipeline stages ---
    raw_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=2000))
    ml_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    db_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=1000))
    
    # --- Progress tracking ---
    total_files: int = 0
    processed_files: int = 0
    cached_files: int = 0
    failed_files: int = 0
    
    logs: List[Dict[str, Any]] = field(default_factory=list)
    tasks: List[asyncio.Task] = field(default_factory=list)
    
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
    
    # The "poison pill" is no longer needed with the join/cancel pattern
    
    try:
        # --- Define and start all workers ---
        scanner_task = asyncio.create_task(io_scanner.scan_directory(ctx, directory_path))
        
        cpu_workers = [
            cpu_processor.process_files(ctx, collection_name)
            for _ in range(2)
        ]
        
        gpu_workers = [
            gpu_worker.process_ml_batches(ctx)
            for _ in range(4)
        ]
        
        db_upserters = [
            db_upserter.upsert_to_db(ctx, collection_name, qdrant_client)
            for _ in range(2)
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


async def start_pipeline(
    directory_path: str,
    collection_name: str,
    background_tasks: BackgroundTasks,
    qdrant_client: QdrantClient
) -> str:
    job_id = str(uuid.uuid4())
    ctx = JobContext(job_id=job_id)
    active_jobs[job_id] = ctx
    
    background_tasks.add_task(
        _run_pipeline,
        job_id,
        directory_path,
        collection_name,
        qdrant_client
    )
    
    logger.info(f"Scheduled pipeline job {job_id} for collection '{collection_name}'")
    return job_id

def get_job_status(job_id: str) -> JobContext | None:
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
