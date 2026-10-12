"""Application factory and ASGI entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_forge import __version__
from fastapi_forge.api.v1.endpoints import health
from fastapi_forge.api.v1.router import api_router
from fastapi_forge.core.config import Settings, get_settings
from fastapi_forge.core.exceptions import register_exception_handlers
from fastapi_forge.core.logging import configure_logging, get_logger
from fastapi_forge.core.middleware import RequestContextMiddleware
from fastapi_forge.core.redis import create_redis_client, create_redis_pool
from fastapi_forge.repos.items import InMemoryItemRepository

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage shared resources for the application's lifetime."""
    settings = get_settings()

    pool = create_redis_pool(settings)
    app.state.redis = create_redis_client(pool)
    app.state.item_repository = InMemoryItemRepository()

    logger.info("application.startup", extra={"environment": settings.environment})
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await pool.disconnect()
        logger.info("application.shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a :class:`FastAPI` application instance."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Production-ready async FastAPI template with Redis caching, "
        "rate limiting and distributed locks.",
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(RequestContextMiddleware, header=settings.request_id_header)

    if settings.cors_origins:
        # Credentials cannot be combined with a wildcard origin.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials="*" not in settings.cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[settings.request_id_header],
        )

    register_exception_handlers(app)

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
