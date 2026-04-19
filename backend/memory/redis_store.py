import json
from typing import Optional, Any
import redis.asyncio as redis
import structlog

from core.config import settings

log = structlog.get_logger()

_pool: Optional[redis.ConnectionPool] = None


async def get_redis() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(settings.REDIS_URL, decode_responses=True)
    return redis.Redis(connection_pool=_pool)


async def set_run_state(run_id: str, state: dict, ttl: int = None):
    r = await get_redis()
    key = f"run:{run_id}:state"
    await r.setex(key, ttl or settings.REDIS_TTL, json.dumps(state))


async def get_run_state(run_id: str) -> Optional[dict]:
    r = await get_redis()
    key = f"run:{run_id}:state"
    data = await r.get(key)
    return json.loads(data) if data else None


async def set_run_status(run_id: str, status: str):
    r = await get_redis()
    await r.setex(f"run:{run_id}:status", settings.REDIS_TTL, status)


async def get_run_status(run_id: str) -> Optional[str]:
    r = await get_redis()
    return await r.get(f"run:{run_id}:status")


async def cache_task_result(task_hash: str, result: dict, ttl: int = 86400):
    """Cache completed task results to avoid duplicate LLM calls."""
    r = await get_redis()
    await r.setex(f"cache:{task_hash}", ttl, json.dumps(result))


async def get_cached_task(task_hash: str) -> Optional[dict]:
    r = await get_redis()
    data = await r.get(f"cache:{task_hash}")
    return json.loads(data) if data else None
