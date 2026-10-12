"""JSON cache built on top of ``redis.asyncio``."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis


class Cache:
    """Namespaced JSON cache with optional TTL.

    Values are (de)serialized with :mod:`json`; any JSON-compatible payload
    works. Keys are transparently prefixed to avoid collisions.
    """

    def __init__(
        self,
        redis: Redis,
        *,
        key_prefix: str = "forge:cache",
        default_ttl: int = 60,
    ) -> None:
        self._redis = redis
        self._prefix = key_prefix
        self._default_ttl = default_ttl

    def _key(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def get(self, key: str) -> Any:
        raw = await self._redis.get(self._key(key))
        if raw is None:
            return None
        return json.loads(raw)

    async def set(self, key: str, value: Any, *, ttl: int | None = None) -> None:
        await self._redis.set(
            self._key(key),
            json.dumps(value, separators=(",", ":"), default=str),
            ex=ttl or self._default_ttl,
        )

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0
        return int(await self._redis.delete(*(self._key(k) for k in keys)))

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(self._key(key)))

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[Any]],
        *,
        ttl: int | None = None,
    ) -> Any:
        """Return the cached value, computing and storing it on a miss."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        if value is not None:
            await self.set(key, value, ttl=ttl)
        return value
