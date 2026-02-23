"""OpenTelemetry initialization helpers for Epstein

Provides a simple `init_tracer()` function that configures a ConsoleSpanExporter by default,
and an OTLP exporter if OTEL_ENABLED/OTEL_EXPORTER_OTLP_ENDPOINT is set.
"""
from __future__ import annotations

import os

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
except Exception:
    # If opentelemetry packages are not installed, provide a stubbed init
    trace = None


def init_tracer(service_name: str | None = None) -> None:
    if trace is None:
        # No-op if opentelemetry not installed
        return

    service_name = service_name or os.getenv("OTEL_SERVICE_NAME", "epstein")
    resource = Resource.create({"service.name": service_name})

    provider = TracerProvider(resource=resource)

    # Console exporter for local debugging
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # OTLP exporter if enabled
    otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() in ("1", "true", "yes")
    if otel_enabled:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4317")
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception:
            # If OTLP exporter cannot be configured, fall back to console
            pass

    trace.set_tracer_provider(provider)


def get_tracer(name: str | None = None):
    if trace is None:
        class NoopTracer:
            def start_as_current_span(self, *a, **k):
                from contextlib import nullcontext
                return nullcontext()
        return NoopTracer()
    return trace.get_tracer(name or __name__)
