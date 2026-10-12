"""Health, readiness and request-id middleware tests."""

from __future__ import annotations

from httpx import AsyncClient


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_with_redis_up(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "up"}


async def test_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/health/live", headers={"X-Request-ID": "trace-123"})
    assert response.headers["x-request-id"] == "trace-123"


async def test_request_id_is_generated_when_missing(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.headers["x-request-id"]
