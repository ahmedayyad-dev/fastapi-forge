"""Redis client factory and lifecycle helpers."""

from __future__ import annotations

from redis.asyncio import ConnectionPool, Redis

from fastapi_forge.core.config import Settings


def create_redis_pool(settings: Settings) -> ConnectionPool:
    """Create a shared connection pool from the configured Redis URL."""
    return ConnectionPool.from_url(
        settings.redis_url,
        max_connections=settings.redis_max_connections,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_socket_timeout,
        decode_responses=True,
        health_check_interval=30,
    )


def create_redis_client(pool: ConnectionPool) -> Redis:
    """Create an async Redis client bound to ``pool``."""
    return Redis(connection_pool=pool)
