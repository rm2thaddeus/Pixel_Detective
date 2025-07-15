import asyncio
import uuid
import logging
import contextlib
from typing import Awaitable, Callable, Dict, Any, Optional

from . import clip_service

logger = logging.getLogger(__name__)

# Internal job structures
_job_queue: asyncio.Queue[tuple[str, Callable[[], Awaitable[Any]]]] = asyncio.Queue()
_job_results: Dict[str, Dict[str, Any]] = {}
_job_events: Dict[str, asyncio.Event] = {}
_scheduler_task: Optional[asyncio.Task] = None

async def _worker() -> None:
    """Background task that processes jobs sequentially under the GPU lock."""
    while True:
        job_id, job_coro = await _job_queue.get()
        try:
            _job_results[job_id] = {"status": "running"}
            async with clip_service.gpu_lock:
                result = await job_coro()
            _job_results[job_id] = {"status": "completed", "result": result}
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            _job_results[job_id] = {"status": "failed", "error": str(e)}
        finally:
            event = _job_events.pop(job_id, None)
            if event:
                event.set()
            _job_queue.task_done()

async def start_scheduler() -> None:
    """Start the background scheduler worker."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_worker())

async def stop_scheduler() -> None:
    """Stop the scheduler worker."""
    if _scheduler_task:
        _scheduler_task.cancel()
        with contextlib.suppress(Exception):
            await _scheduler_task

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Return the current status for a job."""
    return _job_results.get(job_id)

def enqueue_job(coro_func: Callable[[], Awaitable[Any]]) -> str:
    """Enqueue a coroutine for execution and return its job id."""
    job_id = str(uuid.uuid4())
    _job_results[job_id] = {"status": "queued"}
    _job_events[job_id] = asyncio.Event()
    _job_queue.put_nowait((job_id, coro_func))
    return job_id

async def get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Return job result if completed or failed."""
    if job_id in _job_results and _job_results[job_id]["status"] in {"completed", "failed"}:
        return _job_results[job_id]
    event = _job_events.get(job_id)
    if event:
        await event.wait()
    return _job_results.get(job_id)
