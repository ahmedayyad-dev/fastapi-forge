"""ASGI middleware for request-id propagation and access logging."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders

from fastapi_forge.core.logging import request_id_ctx

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("fastapi_forge.access")


class RequestContextMiddleware:
    """Pure-ASGI middleware.

    * reads or generates an ``X-Request-ID``
    * exposes it through a :mod:`contextvars` so logs are correlated
    * echoes it back on the response
    * emits a single JSON access log per request
    """

    def __init__(self, app: ASGIApp, *, header: str = "X-Request-ID") -> None:
        self.app = app
        self.header = header
        self.header_bytes = header.lower().encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope)
        request_id = incoming.get(self.header_bytes.decode("latin-1")) or uuid4().hex
        token = request_id_ctx.set(request_id)

        status_code = 500
        start = perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers[self.header] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception(
                "request.failed",
                extra={
                    "http_method": scope.get("method"),
                    "http_path": scope.get("path"),
                    "http_status": 500,
                },
            )
            raise
        finally:
            duration_ms = round((perf_counter() - start) * 1000, 2)
            logger.info(
                "request.completed",
                extra={
                    "http_method": scope.get("method"),
                    "http_path": scope.get("path"),
                    "http_status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            request_id_ctx.reset(token)
