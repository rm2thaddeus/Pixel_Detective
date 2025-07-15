import asyncio
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List

import torch

logger = logging.getLogger(__name__)

# Type alias for the coroutine that will process a batch of items
BatchProcFn = Callable[[List[Any]], Coroutine[Any, Any, List[Any]]]

@dataclass
class GPUJob:
    """Representation of a GPU job request."""

    job_id: str
    batch: List[Any]
    func: BatchProcFn
    est_vram: int  # bytes required to process the batch


# --- Internal Queues and State ---
_job_queue: asyncio.Queue[GPUJob] = asyncio.Queue()
_job_results: Dict[str, List[Any]] = {}
_job_expected: Dict[str, int] = {}
_job_events: Dict[str, asyncio.Event] = {}

_WORKERS_STARTED = False
_WORKER_COUNT = int(os.environ.get("GPU_SCHEDULER_WORKERS", "1"))


def _ensure_workers_started() -> None:
    global _WORKERS_STARTED
    if _WORKERS_STARTED:
        return
    loop = asyncio.get_event_loop()
    for _ in range(_WORKER_COUNT):
        loop.create_task(_gpu_worker())
    _WORKERS_STARTED = True
    logger.info("GPU job scheduler started with %d worker(s)", _WORKER_COUNT)


async def _gpu_worker() -> None:
    """Background worker that executes jobs when enough GPU memory is available."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    while True:
        job = await _job_queue.get()
        try:
            await _process_job(job, device)
        except Exception as e:
            logger.error("Job %s failed: %s", job.job_id, e, exc_info=True)
            _record_result(job.job_id, [], len(job.batch))
        finally:
            _job_queue.task_done()


async def _process_job(job: GPUJob, device: torch.device) -> None:
    free_mem, _ = torch.cuda.mem_get_info(device) if device.type == "cuda" else (float("inf"), float("inf"))
    if job.est_vram <= free_mem:
        logger.debug("Running job %s with batch size %d", job.job_id, len(job.batch))
        result = await job.func(job.batch)
        _record_result(job.job_id, result, len(job.batch))
    else:
        if len(job.batch) <= 1:
            # Not enough memory even for a single item, wait and requeue
            logger.debug("Insufficient VRAM for single-item job %s, retrying", job.job_id)
            await asyncio.sleep(1)
            await _job_queue.put(job)
            return
        mid = len(job.batch) // 2
        est = max(1, job.est_vram // 2)
        logger.debug(
            "Splitting job %s into two batches of %d and %d due to VRAM limits",
            job.job_id,
            mid,
            len(job.batch) - mid,
        )
        await _job_queue.put(GPUJob(job.job_id, job.batch[:mid], job.func, est))
        await _job_queue.put(GPUJob(job.job_id, job.batch[mid:], job.func, est))


def _record_result(job_id: str, part: List[Any], count: int) -> None:
    results = _job_results.setdefault(job_id, [])
    results.extend(part)
    _job_expected[job_id] -= count
    if _job_expected[job_id] <= 0:
        _job_events[job_id].set()


# --- Public API ---
async def enqueue_job(batch: List[Any], func: BatchProcFn, est_vram: int) -> str:
    """Add a new GPU job to the queue and return its job_id."""
    _ensure_workers_started()
    job_id = str(uuid.uuid4())
    _job_expected[job_id] = len(batch)
    _job_events[job_id] = asyncio.Event()
    await _job_queue.put(GPUJob(job_id, batch, func, est_vram))
    return job_id


async def get_job_result(job_id: str) -> List[Any]:
    """Wait for a job to finish and return its aggregated results."""
    event = _job_events.get(job_id)
    if not event:
        return []
    await event.wait()
    return _job_results.pop(job_id, [])

