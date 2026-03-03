"""Request middleware: correlation IDs and structured access logging."""

from __future__ import annotations

import time
import uuid
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.logging import get_logger

logger = get_logger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach correlation/request IDs to every request and response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        clear_contextvars()

        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        request_id = str(uuid.uuid4())

        bind_contextvars(
            correlation_id=correlation_id,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers[CORRELATION_ID_HEADER] = correlation_id
        response.headers[REQUEST_ID_HEADER] = request_id

        logger.info(
            "http.request",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        clear_contextvars()
        return response
