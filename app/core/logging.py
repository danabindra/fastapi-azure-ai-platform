"""Structured JSON logging via structlog.

Includes OpenTelemetry trace/span IDs in every log record so logs
correlate with distributed traces in Application Insights.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace

from app.core.config import get_settings


def _add_otel_context(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Inject active OTel trace/span IDs into each log record."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.is_valid:
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def configure_logging() -> None:
    """Configure structlog with JSON output and OTel context injection."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_otel_context,
        structlog.processors.StackInfoRenderer(),
    ]

    if sys.stderr.isatty() and settings.app_env == "local":
        # Pretty console output for local dev
        renderer: Any = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *shared_processors,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    # Reduce noise from third-party libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[return-value]
