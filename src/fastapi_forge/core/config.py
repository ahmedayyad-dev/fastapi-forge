"""Application configuration powered by pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables / ``.env``.

    Every field can be overridden with an environment variable using the
    ``FORGE_`` prefix, e.g. ``FORGE_REDIS_URL=redis://cache:6379/1``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FORGE_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application --------------------------------------------------------
    app_name: str = "fastapi-forge"
    environment: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Redis --------------------------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: Annotated[int, Field(gt=0)] = 20
    redis_socket_timeout: Annotated[float, Field(gt=0)] = 5.0

    # --- Cache --------------------------------------------------------------
    cache_ttl_seconds: Annotated[int, Field(gt=0)] = 60

    # --- Rate limiting ------------------------------------------------------
    rate_limit_requests: Annotated[int, Field(gt=0)] = 100
    rate_limit_window_seconds: Annotated[int, Field(gt=0)] = 60

    # --- Distributed lock ---------------------------------------------------
    lock_ttl_seconds: Annotated[int, Field(gt=0)] = 30
    lock_blocking_timeout_seconds: Annotated[float, Field(ge=0)] = 5.0
    lock_poll_interval_seconds: Annotated[float, Field(gt=0)] = 0.1

    # --- Logging ------------------------------------------------------------
    log_level: str = "INFO"
    log_json: bool = True

    # --- Middleware ---------------------------------------------------------
    request_id_header: str = "X-Request-ID"

    # --- CORS ---------------------------------------------------------------
    cors_origins: list[str] = Field(default_factory=list)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        """Accept ``"*"``, ``"a,b"`` or a JSON list for CORS origins."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped or stripped == "*":
                return ["*"] if stripped == "*" else []
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance."""
    return Settings()
