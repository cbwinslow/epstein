"""
OpenTelemetry Instrumentation for Multi-Agent System
Provides comprehensive tracing, metrics, and logging for all agents.
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Status, StatusCode


class AgentTelemetry:
    """
    Centralized telemetry management for multi-agent system.
    """

    def __init__(
        self,
        service_name: str = "epstein-multi-agent-system",
        enable_console_export: bool = True,
        enable_otlp_export: bool = False,
        otlp_endpoint: str | None = None,
    ):
        """
        Initialize telemetry with OpenTelemetry SDK.

        Args:
            service_name: Name of the service for telemetry
            enable_console_export: Export to console for debugging
            enable_otlp_export: Export to OTLP collector
            otlp_endpoint: OTLP collector endpoint (e.g., "localhost:4317")
        """
        self.service_name = service_name
        self.logger = logging.getLogger(__name__)

        # Create resource with service information
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": "1.0.0",
                "deployment.environment": "development",
            }
        )

        # Setup tracing
        self._setup_tracing(resource, enable_console_export, enable_otlp_export, otlp_endpoint)

        # Setup metrics
        self._setup_metrics(resource, enable_console_export, enable_otlp_export, otlp_endpoint)

        # Get tracer and meter
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)

        # Create metrics
        self._create_metrics()

        # Agent performance tracking
        self.agent_metrics = {}

    def _setup_tracing(self, resource: Resource, console: bool, otlp: bool, endpoint: str | None):
        """Setup tracing with exporters"""
        tracer_provider = TracerProvider(resource=resource)

        # Add console exporter for debugging
        if console:
            console_exporter = ConsoleSpanExporter()
            tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

        # Add OTLP exporter for production
        if otlp and endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(tracer_provider)

    def _setup_metrics(self, resource: Resource, console: bool, otlp: bool, endpoint: str | None):
        """Setup metrics with exporters"""
        readers = []

        # Add console exporter for debugging
        if console:
            console_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(), export_interval_millis=60000  # Export every 60 seconds
            )
            readers.append(console_reader)

        # Add OTLP exporter for production
        if otlp and endpoint:
            otlp_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=endpoint, insecure=True), export_interval_millis=60000
            )
            readers.append(otlp_reader)

        meter_provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(meter_provider)

    def _create_metrics(self):
        """Create standard metrics for agents"""
        # Counter for agent executions
        self.agent_execution_counter = self.meter.create_counter(
            name="agent.executions", description="Number of agent executions", unit="1"
        )

        # Counter for agent errors
        self.agent_error_counter = self.meter.create_counter(
            name="agent.errors", description="Number of agent errors", unit="1"
        )

        # Histogram for agent execution duration
        self.agent_duration_histogram = self.meter.create_histogram(
            name="agent.duration", description="Agent execution duration", unit="ms"
        )

        # Counter for task completions
        self.task_completion_counter = self.meter.create_counter(
            name="task.completions", description="Number of completed tasks", unit="1"
        )

        # Gauge for active agents
        self.active_agents_gauge = self.meter.create_observable_gauge(
            name="agent.active",
            description="Number of active agents",
            callbacks=[self._get_active_agents],
        )

    def _get_active_agents(self, options: CallbackOptions) -> list[Observation]:
        """Callback for active agents gauge"""
        active_count = len([m for m in self.agent_metrics.values() if m.get("status") == "running"])
        return [Observation(active_count)]

    def trace_agent_execution(self, agent_name: str):
        """
        Decorator to trace agent execution with OpenTelemetry.

        Args:
            agent_name: Name of the agent being traced

        Returns:
            Decorated function with tracing
        """

        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Start span
                with self.tracer.start_as_current_span(
                    f"{agent_name}.{func.__name__}",
                    attributes={
                        "agent.name": agent_name,
                        "agent.method": func.__name__,
                        "agent.type": "async",
                    },
                ) as span:
                    start_time = time.time()

                    try:
                        # Update agent status
                        self.agent_metrics[agent_name] = {
                            "status": "running",
                            "start_time": start_time,
                        }

                        # Record execution
                        self.agent_execution_counter.add(
                            1, {"agent.name": agent_name, "method": func.__name__}
                        )

                        # Execute function
                        result = await func(*args, **kwargs)

                        # Calculate duration
                        duration_ms = (time.time() - start_time) * 1000

                        # Record duration
                        self.agent_duration_histogram.record(
                            duration_ms, {"agent.name": agent_name, "method": func.__name__}
                        )

                        # Update span with success
                        span.set_status(Status(StatusCode.OK))
                        span.set_attribute("agent.duration_ms", duration_ms)
                        span.set_attribute("agent.status", "success")

                        # Update agent status
                        self.agent_metrics[agent_name] = {
                            "status": "completed",
                            "duration": duration_ms,
                        }

                        # Record task completion
                        self.task_completion_counter.add(
                            1, {"agent.name": agent_name, "status": "success"}
                        )

                        return result

                    except Exception as e:
                        # Calculate duration
                        duration_ms = (time.time() - start_time) * 1000

                        # Record error
                        self.agent_error_counter.add(
                            1, {"agent.name": agent_name, "error.type": type(e).__name__}
                        )

                        # Update span with error
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.set_attribute("agent.duration_ms", duration_ms)
                        span.set_attribute("agent.status", "error")
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                        span.record_exception(e)

                        # Update agent status
                        self.agent_metrics[agent_name] = {
                            "status": "failed",
                            "error": str(e),
                            "duration": duration_ms,
                        }

                        # Record task completion with error
                        self.task_completion_counter.add(
                            1, {"agent.name": agent_name, "status": "error"}
                        )

                        raise

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Start span
                with self.tracer.start_as_current_span(
                    f"{agent_name}.{func.__name__}",
                    attributes={
                        "agent.name": agent_name,
                        "agent.method": func.__name__,
                        "agent.type": "sync",
                    },
                ) as span:
                    start_time = time.time()

                    try:
                        # Update agent status
                        self.agent_metrics[agent_name] = {
                            "status": "running",
                            "start_time": start_time,
                        }

                        # Record execution
                        self.agent_execution_counter.add(
                            1, {"agent.name": agent_name, "method": func.__name__}
                        )

                        # Execute function
                        result = func(*args, **kwargs)

                        # Calculate duration
                        duration_ms = (time.time() - start_time) * 1000

                        # Record duration
                        self.agent_duration_histogram.record(
                            duration_ms, {"agent.name": agent_name, "method": func.__name__}
                        )

                        # Update span with success
                        span.set_status(Status(StatusCode.OK))
                        span.set_attribute("agent.duration_ms", duration_ms)
                        span.set_attribute("agent.status", "success")

                        # Update agent status
                        self.agent_metrics[agent_name] = {
                            "status": "completed",
                            "duration": duration_ms,
                        }

                        # Record task completion
                        self.task_completion_counter.add(
                            1, {"agent.name": agent_name, "status": "success"}
                        )

                        return result

                    except Exception as e:
                        # Calculate duration
                        duration_ms = (time.time() - start_time) * 1000

                        # Record error
                        self.agent_error_counter.add(
                            1, {"agent.name": agent_name, "error.type": type(e).__name__}
                        )

                        # Update span with error
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.set_attribute("agent.duration_ms", duration_ms)
                        span.set_attribute("agent.status", "error")
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_attribute("error.message", str(e))
                        span.record_exception(e)

                        # Update agent status
                        self.agent_metrics[agent_name] = {
                            "status": "failed",
                            "error": str(e),
                            "duration": duration_ms,
                        }

                        # Record task completion with error
                        self.task_completion_counter.add(
                            1, {"agent.name": agent_name, "status": "error"}
                        )

                        raise

            # Return appropriate wrapper based on function type
            import asyncio

            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def create_span(self, name: str, attributes: dict[str, Any] | None = None):
        """
        Create a new span for custom tracing.

        Args:
            name: Name of the span
            attributes: Optional attributes to add to the span

        Returns:
            Span context manager
        """
        return self.tracer.start_as_current_span(name, attributes=attributes or {})

    def record_metric(
        self, metric_name: str, value: float, attributes: dict[str, str] | None = None
    ):
        """
        Record a custom metric.

        Args:
            metric_name: Name of the metric
            value: Value to record
            attributes: Optional attributes for the metric
        """
        # This would create a custom metric if needed
        pass

    def get_agent_metrics(self) -> dict[str, Any]:
        """
        Get current agent metrics.

        Returns:
            Dictionary of agent metrics
        """
        return {"agents": self.agent_metrics, "timestamp": datetime.now().isoformat()}

    def shutdown(self):
        """Shutdown telemetry providers"""
        try:
            # Shutdown tracer provider
            tracer_provider = trace.get_tracer_provider()
            if hasattr(tracer_provider, "shutdown"):
                tracer_provider.shutdown()

            # Shutdown meter provider
            meter_provider = metrics.get_meter_provider()
            if hasattr(meter_provider, "shutdown"):
                meter_provider.shutdown()

        except Exception as e:
            self.logger.error(f"Error shutting down telemetry: {e}")


# Global telemetry instance
_telemetry_instance = None


def get_telemetry(
    service_name: str = "epstein-multi-agent-system",
    enable_console_export: bool = True,
    enable_otlp_export: bool = False,
    otlp_endpoint: str | None = None,
) -> AgentTelemetry:
    """
    Get or create global telemetry instance.

    Args:
        service_name: Name of the service
        enable_console_export: Export to console
        enable_otlp_export: Export to OTLP collector
        otlp_endpoint: OTLP collector endpoint

    Returns:
        AgentTelemetry instance
    """
    global _telemetry_instance

    if _telemetry_instance is None:
        _telemetry_instance = AgentTelemetry(
            service_name=service_name,
            enable_console_export=enable_console_export,
            enable_otlp_export=enable_otlp_export,
            otlp_endpoint=otlp_endpoint,
        )

    return _telemetry_instance


# Convenience decorator for tracing
def trace_agent(agent_name: str):
    """
    Convenience decorator for tracing agent methods.

    Args:
        agent_name: Name of the agent

    Returns:
        Decorator function
    """
    telemetry = get_telemetry()
    return telemetry.trace_agent_execution(agent_name)
