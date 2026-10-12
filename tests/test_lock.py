"""Tests for the Redis distributed lock."""

from __future__ import annotations

import pytest
from redis.asyncio import Redis

from fastapi_forge.core.lock import LockNotAcquiredError, RedisLock


async def test_mutual_exclusion(redis: Redis) -> None:
    first = RedisLock(redis, "resource", ttl=10)
    second = RedisLock(redis, "resource", ttl=10, blocking_timeout=0)

    assert await first.acquire() is True
    assert await second.acquire() is False

    assert await first.release() is True
    assert await second.acquire() is True
    await second.release()


async def test_context_manager(redis: Redis) -> None:
    lock = RedisLock(redis, "ctx", ttl=10)
    async with lock:
        assert lock.locked is True
    assert lock.locked is False


async def test_timeout_raises(redis: Redis) -> None:
    holder = RedisLock(redis, "contended", ttl=10)
    await holder.acquire()

    with pytest.raises(LockNotAcquiredError):
        async with RedisLock(redis, "contended", ttl=10, blocking_timeout=0):
            pass

    await holder.release()
