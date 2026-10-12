"""Reusable FastAPI dependencies (DI wiring)."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis

from fastapi_forge.core.cache import Cache
from fastapi_forge.core.config import Settings, get_settings
from fastapi_forge.core.exceptions import RateLimitedError
from fastapi_forge.core.rate_limit import RateLimiter
from fastapi_forge.repos.items import ItemRepository
from fastapi_forge.services.items import ItemService


def get_redis(request: Request) -> Redis:
    """Return the application-wide Redis client."""
    return cast("Redis", request.app.state.redis)


def get_repository(request: Request) -> ItemRepository:
    """Return the configured item repository."""
    return cast("ItemRepository", request.app.state.item_repository)


def get_cache(
    redis: Annotated[Redis, Depends(get_redis)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Cache:
    """Build a request-scoped cache facade."""
    return Cache(redis, default_ttl=settings.cache_ttl_seconds)


def get_item_service(
    repository: Annotated[ItemRepository, Depends(get_repository)],
    cache: Annotated[Cache, Depends(get_cache)],
) -> ItemService:
    """Build the item service with its dependencies."""
    return ItemService(repository, cache)


class RateLimit:
    """Dependency that enforces a per-client sliding-window rate limit.

    Instantiate with custom limits or rely on the values from settings::

        @router.get("/search", dependencies=[Depends(RateLimit(requests=10, window_seconds=60))])
    """

    def __init__(self, requests: int | None = None, window_seconds: int | None = None) -> None:
        self._requests = requests
        self._window_seconds = window_seconds

    async def __call__(
        self,
        request: Request,
        redis: Annotated[Redis, Depends(get_redis)],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> None:
        limiter = RateLimiter(
            redis,
            limit=self._requests or settings.rate_limit_requests,
            window_seconds=self._window_seconds or settings.rate_limit_window_seconds,
        )
        client_host = request.client.host if request.client else "anonymous"
        result = await limiter.check(f"{request.url.path}:{client_host}")
        if not result.allowed:
            raise RateLimitedError("Rate limit exceeded. Please retry later.")
