"""OpenTelemetry setup for FastAPI, SQLAlchemy, and HTTPX.

Exporters (in priority order):
  1. Azure Monitor (Application Insights) if APPLICATIONINSIGHTS_CONNECTION_STRING is set
  2. OTLP gRPC if OTEL_EXPORTER_OTLP_ENDPOINT is set
  3. No-op (telemetry is still collected, just not exported)
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_exporter(settings: Settings) -> SpanExporter | None:
    if settings.applicationinsights_connection_string:
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            logger.info("telemetry.exporter", kind="azure_monitor")
            return AzureMonitorTraceExporter(
                connection_string=settings.applicationinsights_connection_string
            )
        except ImportError:
            logger.warning(
                "telemetry.exporter",
                warning="azure-monitor-opentelemetry-exporter not installed; falling back to OTLP",
            )

    if settings.otel_exporter_otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        logger.info(
            "telemetry.exporter",
            kind="otlp",
            endpoint=settings.otel_exporter_otlp_endpoint,
        )
        return OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)

    return None


def setup_telemetry(settings: Settings) -> TracerProvider:
    """Initialise OTel SDK and instrument FastAPI / SQLAlchemy / HTTPX."""
    resource = Resource(attributes={SERVICE_NAME: settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    exporter = _build_exporter(settings)
    if exporter:
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        logger.info("telemetry.exporter", kind="noop")

    trace.set_tracer_provider(provider)

    SQLAlchemyInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    # FastAPI instrumentation is applied after the app object is created;
    # call instrument_app(app) from main.py after app creation.

    return provider


def instrument_app(app: object) -> None:
    """Attach FastAPI instrumentation to the ASGI app instance."""
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]
