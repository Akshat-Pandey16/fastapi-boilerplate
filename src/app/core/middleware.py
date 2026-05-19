"""Custom ASGI middleware: request IDs, access logging, timing."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger, request_id_ctx

logger = get_logger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and emit structured access logs."""

    def __init__(self, app: ASGIApp, *, header_name: str | None = None) -> None:
        super().__init__(app)
        self.header_name = header_name or settings.request_id_header

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()

        log = logger.bind(
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            log.exception("request_failed", duration_ms=round(duration_ms, 2))
            raise
        else:
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers[self.header_name] = request_id
            response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"
            log.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            return response
        finally:
            request_id_ctx.reset(token)


__all__ = ["RequestContextMiddleware"]
