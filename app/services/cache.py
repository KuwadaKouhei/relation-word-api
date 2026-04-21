import hashlib
import json
from typing import Any

from cachetools import TTLCache

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None  # type: ignore[assignment]

from app.core.config import get_settings
from app.core.logging import logger

_local: TTLCache[str, Any] = TTLCache(maxsize=10_000, ttl=get_settings().cache_ttl_seconds)
_redis: "aioredis.Redis | None" = None


def _init_redis() -> "aioredis.Redis | None":
    global _redis
    if _redis is not None or aioredis is None:
        return _redis
    try:
        _redis = aioredis.from_url(
            get_settings().redis_url, encoding="utf-8", decode_responses=True
        )
    except Exception as e:
        logger.warning("redis_init_failed", error=str(e))
        _redis = None
    return _redis


def make_key(namespace: str, parts: dict[str, Any]) -> str:
    payload = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"{namespace}:{digest}"


async def get(key: str) -> Any | None:
    if key in _local:
        return _local[key]
    r = _init_redis()
    if r is None:
        return None
    try:
        raw = await r.get(key)
    except Exception as e:
        logger.warning("redis_get_failed", error=str(e))
        return None
    if raw is None:
        return None
    try:
        value = json.loads(raw)
        _local[key] = value
        return value
    except json.JSONDecodeError:
        return None


async def set(key: str, value: Any) -> None:
    _local[key] = value
    r = _init_redis()
    if r is None:
        return
    try:
        await r.set(key, json.dumps(value, ensure_ascii=False), ex=get_settings().cache_ttl_seconds)
    except Exception as e:
        logger.warning("redis_set_failed", error=str(e))
