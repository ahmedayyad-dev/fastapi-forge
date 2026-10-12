"""Shared pytest fixtures wired around fakeredis and the ASGI app."""

from __future__ import annotations

from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from fastapi_forge.api import deps
from fastapi_forge.core.cache import Cache
from fastapi_forge.main import create_app
from fastapi_forge.repos.items import InMemoryItemRepository
from fastapi_forge.services.items import ItemService


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    """An isolated in-process Redis replacement."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def repository() -> InMemoryItemRepository:
    return InMemoryItemRepository()


@pytest.fixture
async def cache(redis: Redis) -> Cache:
    return Cache(redis, default_ttl=60)


@pytest.fixture
async def app(
    redis: Redis,
    repository: InMemoryItemRepository,
    cache: Cache,
) -> AsyncIterator[FastAPI]:
    application = create_app()
    service = ItemService(repository, cache)
    application.dependency_overrides[deps.get_redis] = lambda: redis
    application.dependency_overrides[deps.get_repository] = lambda: repository
    application.dependency_overrides[deps.get_item_service] = lambda: service
    try:
        yield application
    finally:
        application.dependency_overrides.clear()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
