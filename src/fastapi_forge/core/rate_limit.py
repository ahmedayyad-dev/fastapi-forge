"""Atomic sliding-window rate limiter backed by Redis."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from redis.asyncio import Redis

# Runs atomically on the server: trim the window, count, then decide.
_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

if count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('PEXPIRE', key, window)
    return {1, limit - count - 1}
end

return {0, 0}
"""


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    """Outcome of a rate-limit check."""

    allowed: bool
    remaining: int
    limit: int


class RateLimiter:
    """Sliding-window limiter: at most ``limit`` hits per ``window_seconds``."""

    def __init__(
        self,
        redis: Redis,
        *,
        limit: int,
        window_seconds: int,
        key_prefix: str = "forge:ratelimit",
    ) -> None:
        self._redis = redis
        self._limit = limit
        self._window_ms = window_seconds * 1000
        self._prefix = key_prefix
        self._script = redis.register_script(_SLIDING_WINDOW_SCRIPT)

    async def check(self, identifier: str) -> RateLimitResult:
        """Register a hit for ``identifier`` and report whether it is allowed."""
        now_ms = await self._now_ms()
        key = f"{self._prefix}:{identifier}"
        allowed, remaining = await self._script(
            keys=[key],
            args=[now_ms, self._window_ms, self._limit, uuid4().hex],
        )
        return RateLimitResult(
            allowed=bool(allowed),
            remaining=int(remaining),
            limit=self._limit,
        )

    async def _now_ms(self) -> int:
        seconds, microseconds = await self._redis.time()
        return int(seconds) * 1000 + int(microseconds) // 1000
