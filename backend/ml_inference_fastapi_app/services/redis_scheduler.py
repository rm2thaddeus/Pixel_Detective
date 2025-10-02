import asyncio
import uuid
import logging
import os
from typing import Awaitable, Callable, Dict, Any, Optional
import aioredis
import pickle

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
JOB_QUEUE_KEY = "ml_jobs:queue"
JOB_STATUS_KEY = "ml_jobs:status"
JOB_RESULT_KEY = "ml_jobs:result"

_redis: Optional[aioredis.Redis] = None
_worker_task: Optional[asyncio.Task] = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(REDIS_URL, decode_responses=False)
    return _redis

async def enqueue_job(coro_func: Callable[[], Awaitable[Any]]) -> str:
    """Enqueue a coroutine for execution and return its job id."""
    job_id = str(uuid.uuid4())
    redis = await get_redis()
    # Serialize the coroutine function using pickle
    job_data = pickle.dumps(coro_func)
    await redis.hset(JOB_STATUS_KEY, job_id, pickle.dumps({"status": "queued"}))
    await redis.rpush(JOB_QUEUE_KEY, pickle.dumps((job_id, job_data)))
    return job_id

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    redis = await get_redis()
    data = await redis.hget(JOB_STATUS_KEY, job_id)
    if data is None:
        return None
    return pickle.loads(data)

async def set_job_status(job_id: str, status: Dict[str, Any]):
    redis = await get_redis()
    await redis.hset(JOB_STATUS_KEY, job_id, pickle.dumps(status))

async def set_job_result(job_id: str, result: Dict[str, Any]):
    redis = await get_redis()
    await redis.hset(JOB_RESULT_KEY, job_id, pickle.dumps(result))

async def get_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    redis = await get_redis()
    data = await redis.hget(JOB_RESULT_KEY, job_id)
    if data is None:
        return None
    return pickle.loads(data)

async def _worker():
    redis = await get_redis()
    while True:
        job = await redis.blpop(JOB_QUEUE_KEY, timeout=5)
        if job is None:
            await asyncio.sleep(1)
            continue
        _, job_data = job
        job_id, coro_func_data = pickle.loads(job_data)
        try:
            await set_job_status(job_id, {"status": "running"})
            coro_func = pickle.loads(coro_func_data)
            result = await coro_func()
            await set_job_status(job_id, {"status": "completed", "result": result})
            await set_job_result(job_id, {"result": result})
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            await set_job_status(job_id, {"status": "failed", "error": str(e)})
        # No event notification; polling is used for now

async def start_scheduler():
    global _worker_task
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_worker())

async def stop_scheduler():
    global _worker_task
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except Exception:
            pass
    # Optionally close Redis connection
    global _redis
    if _redis:
        await _redis.close()
        _redis = None 