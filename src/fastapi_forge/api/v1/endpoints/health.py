"""Liveness and readiness probes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from fastapi_forge.api.deps import get_redis

router = APIRouter()


@router.get("/live", summary="Liveness probe")
async def live() -> dict[str, str]:
    """Return ``200`` as long as the process is running."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def ready(redis: Annotated[Redis, Depends(get_redis)]) -> JSONResponse:
    """Return ``200`` only when dependencies (Redis) are reachable."""
    try:
        await redis.ping()
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable", "redis": "down"},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ok", "redis": "up"})
