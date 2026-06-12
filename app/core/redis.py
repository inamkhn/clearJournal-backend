import json
import redis
from typing import Any, Optional
from app.core.config import settings

_redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Return a singleton Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL, decode_responses=True
        )
    return _redis_client


def redis_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Set a JSON-serialisable value in Redis with a TTL (seconds)."""
    r = get_redis()
    r.set(key, json.dumps(value), ex=ttl)


def redis_get(key: str) -> Optional[Any]:
    """Get a JSON-deserialised value from Redis, or None if missing."""
    r = get_redis()
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


def redis_delete(key: str) -> None:
    """Delete a key from Redis."""
    r = get_redis()
    r.delete(key)


def redis_keys(pattern: str) -> list:
    """Return all keys matching a glob pattern."""
    r = get_redis()
    return r.keys(pattern)
