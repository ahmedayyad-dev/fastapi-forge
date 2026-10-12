"""Tests for the sliding-window rate limiter."""

from __future__ import annotations

from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import Redis

from fastapi_forge.core.config import Settings, get_settings
from fastapi_forge.core.rate_limit import RateLimiter


async def test_limiter_allows_then_blocks(redis: Redis) -> None:
    limiter = RateLimiter(redis, limit=3, window_seconds=60)

    results = [await limiter.check("client-a") for _ in range(3)]
    assert [result.allowed for result in results] == [True, True, True]
    assert [result.remaining for result in results] == [2, 1, 0]

    blocked = await limiter.check("client-a")
    assert blocked.allowed is False
    assert blocked.remaining == 0


async def test_limiters_are_isolated_per_identifier(redis: Redis) -> None:
    limiter = RateLimiter(redis, limit=1, window_seconds=60)
    assert (await limiter.check("client-a")).allowed is True
    assert (await limiter.check("client-b")).allowed is True
    assert (await limiter.check("client-a")).allowed is False


async def test_endpoint_returns_429_when_exceeded(client: AsyncClient, app: FastAPI) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        rate_limit_requests=2, rate_limit_window_seconds=60
    )

    assert (await client.get("/api/v1/items")).status_code == 200
    assert (await client.get("/api/v1/items")).status_code == 200

    limited = await client.get("/api/v1/items")
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "rate_limited"
