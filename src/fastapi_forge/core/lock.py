"""Distributed lock implemented with Redis SET NX PX + a Lua release."""

from __future__ import annotations

import asyncio
from types import TracebackType
from uuid import uuid4

from redis.asyncio import Redis

# Delete the key only when we still own it (compare-and-delete).
_RELEASE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class LockNotAcquiredError(RuntimeError):
    """Raised when a lock cannot be acquired within the blocking timeout."""


class RedisLock:
    """A distributed mutex guarded by a random ownership token.

    Usage::

        lock = RedisLock(redis, "orders:42", ttl=30)
        async with lock:
            ...  # critical section
    """

    def __init__(
        self,
        redis: Redis,
        key: str,
        *,
        ttl: int = 30,
        blocking_timeout: float = 5.0,
        poll_interval: float = 0.1,
        key_prefix: str = "forge:lock",
    ) -> None:
        self._redis = redis
        self._key = f"{key_prefix}:{key}"
        self._ttl_ms = ttl * 1000
        self._blocking_timeout = blocking_timeout
        self._poll_interval = poll_interval
        self._token: str | None = None
        self._release = redis.register_script(_RELEASE_SCRIPT)

    @property
    def key(self) -> str:
        return self._key

    @property
    def locked(self) -> bool:
        return self._token is not None

    async def acquire(self) -> bool:
        """Try to acquire the lock, polling until ``blocking_timeout``."""
        if self._token is not None:
            raise RuntimeError("Lock is already held by this instance")

        token = uuid4().hex
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._blocking_timeout

        while True:
            acquired = await self._redis.set(self._key, token, nx=True, px=self._ttl_ms)
            if acquired:
                self._token = token
                return True
            if loop.time() >= deadline:
                return False
            await asyncio.sleep(self._poll_interval)

    async def release(self) -> bool:
        """Release the lock if this instance still owns it."""
        if self._token is None:
            return False
        released = await self._release(keys=[self._key], args=[self._token])
        self._token = None
        return bool(released)

    async def __aenter__(self) -> RedisLock:
        if not await self.acquire():
            raise LockNotAcquiredError(f"Could not acquire lock {self._key!r}")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.release()
