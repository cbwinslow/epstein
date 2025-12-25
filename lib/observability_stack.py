#!/usr/bin/env python3
"""
Epstein Files Project - Observability Stack

Comprehensive observability integration using:
- OpenTelemetry for distributed tracing and metrics
- LangSmith for LLM observability and monitoring
- LangFuse for LLM evaluation and monitoring
- Prometheus/Grafana for metrics visualization
- Custom monitoring agents for system health

Features:
- Distributed tracing across all components
- LLM observability and cost tracking
- Performance metrics and alerting
- Custom monitoring agents
- Integration with LangChain ecosystem
"""

import asyncio
import json
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
from uuid import uuid4

import psutil
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.aiohttp import AioHttpInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.semconv.resource import ResourceAttributes

# LangChain and LLM observability
try:
    import langchain
    from langchain.callbacks.tracers.langchain import LangChainTracer
    from langchain.callbacks.tracers.langfuse import LangFuseCallbackHandler
    from langchain.callbacks.tracers.stdout import ConsoleCallbackHandler
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️  LangChain not available. Install with: pip install langchain")

# LangSmith integration
try:
    import langsmith
    from langsmith import Client as LangSmithClient
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    print("⚠️  LangSmith not available. Install with: pip install langsmith")

# LangFuse integration
try:
    import langfuse
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    print("⚠️  LangFuse not available. Install with: pip install langfuse")

# Prometheus integration
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("⚠️  Prometheus not available. Install with: pip install prometheus_client")


# Configure logging
logger = logging.getLogger("epstein_observability")


@dataclass
class ObservabilityConfig:
    """Configuration for observability stack"""
    # OpenTelemetry
    otel_service_name: str = "epstein_files"
    otel_service_version: str = "1.0.0"
    otel_exporter_endpoint: str = "http://localhost:4318"
    otel_export_interval: int = 30000  # 30 seconds
    
    # LangSmith
    langsmith_enabled: bool = True
    langsmith_api_key: Optional[str] = None
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "epstein_files"
    
    # LangFuse
    langfuse_enabled: bool = True
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    
    # Prometheus
    prometheus_enabled: bool = True
    prometheus_port: int = 8000
    
    # Custom metrics
    custom_metrics_enabled: bool = True
    system_monitoring_enabled: bool = True
    performance_monitoring_enabled: bool = True


class CustomMetrics:
    """Custom metrics for Epstein Files project"""
    
    def __init__(self):
        if not PROMETHEUS_AVAILABLE:
            logger.warning("⚠️  Prometheus not available, custom metrics disabled")
            return
        
        # Document processing metrics
        self.documents_processed = Counter(
            'epstein_documents_processed_total',
            'Total number of documents processed',
            ['source', 'status']
        )
        
        self.document_processing_time = Histogram(
            'epstein_document_processing_duration_seconds',
            'Time spent processing documents',
            ['source', 'document_type']
        )
        
        self.ocr_processing_time = Histogram(
            'epstein_ocr_processing_duration_seconds',
            'Time spent on OCR processing',
            ['document_type']
        )
        
        self.ner_processing_time = Histogram(
            'epstein_ner_processing_duration_seconds',
            'Time spent on NER processing',
            ['entity_type']
        )
        
        # System metrics
        self.system_cpu_usage = Gauge(
            'epstein_system_cpu_usage_percent',
            'System CPU usage percentage'
        )
        
        self.system_memory_usage = Gauge(
            'epstein_system_memory_usage_percent',
            'System memory usage percentage'
        )
        
        self.system_disk_usage = Gauge(
            'epstein_system_disk_usage_percent',
            'System disk usage percentage'
        )
        
        self.active_workers = Gauge(
            'epstein_active_workers',
            'Number of active worker threads/processes',
            ['pool_type']
        )
        
        # LLM metrics
        self.llm_calls = Counter(
            'epstein_llm_calls_total',
            'Total number of LLM API calls',
            ['model', 'provider', 'status']
        )
        
        self.llm_response_time = Histogram(
            'epstein_llm_response_duration_seconds',
            'LLM API response time',
            ['model', 'provider']
        )
        
        self.llm_tokens_used = Counter(
            'epstein_llm_tokens_used_total',
            'Total number of tokens used',
            ['model', 'provider', 'token_type']
        )
        
        # Database metrics
        self.database_queries = Counter(
            'epstein_database_queries_total',
            'Total number of database queries',
            ['query_type', 'table']
        )
        
        self.database_query_time = Histogram(
            'epstein_database_query_duration_seconds',
            'Database query execution time',
            ['query_type', 'table']
        )
        
        # MCP server metrics
        self.mcp_requests = Counter(
            'epstein_mcp_requests_total',
            'Total number of MCP requests',
            ['endpoint', 'method', 'status']
        )
        
        self.mcp_request_time = Histogram(
            'epstein_mcp_request_duration_seconds',
            'MCP request processing time',
            ['endpoint', 'method']
        )
        
        logger.info("📊 Custom metrics initialized")


class SystemMonitor:
    """System resource monitoring"""
    
    def __init__(self, metrics: CustomMetrics):
        self.metrics = metrics
        self.monitoring = False
        self.monitor_task = None
    
    async def start_monitoring(self):
        """Start system monitoring"""
        if not self.monitoring:
            self.monitoring = True
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("🖥️  System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("🖥️  System monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Update Prometheus metrics
                if PROMETHEUS_AVAILABLE:
                    self.metrics.system_cpu_usage.set(cpu_percent)
                    self.metrics.system_memory_usage.set(memory.percent)
                    self.metrics.system_disk_usage.set(disk.percent)
                
                # Log system status
                logger.debug(
                    f"🖥️  System Status - CPU: {cpu_percent:.1f}%, "
                    f"Memory: {memory.percent:.1f}%, "
                    f"Disk: {disk.percent:.1f}%"
                )
                
                await asyncio.sleep(10)  # Monitor every 10 seconds
            
            except Exception as e:
                logger.error(f"❌ System monitoring error: {e}")
                await asyncio.sleep(5)


class LLMObserver:
    """LLM observability and monitoring"""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.callbacks = []
        
        # Initialize LangSmith
        if LANGSMITH_AVAILABLE and config.langsmith_enabled:
            self._init_langsmith()
        
        # Initialize LangFuse
        if LANGFUSE_AVAILABLE and config.langfuse_enabled:
            self._init_langfuse()
        
        # Initialize console callbacks
        if LANGCHAIN_AVAILABLE:
            self.callbacks.append(ConsoleCallbackHandler())
        
        logger.info("🤖 LLM observability initialized")
    
    def _init_langsmith(self):
        """Initialize LangSmith integration"""
        try:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = self.config.langsmith_api_key
            os.environ["LANGCHAIN_PROJECT"] = self.config.langsmith_project
            os.environ["LANGCHAIN_ENDPOINT"] = self.config.langsmith_endpoint
            
            if LANGCHAIN_AVAILABLE:
                self.callbacks.append(LangChainTracer())
            
            logger.info("🔗 LangSmith integration enabled")
        except Exception as e:
            logger.error(f"❌ LangSmith initialization failed: {e}")
    
    def _init_langfuse(self):
        """Initialize LangFuse integration"""
        try:
            if LANGCHAIN_AVAILABLE:
                callback = LangFuseCallbackHandler(
                    secret_key=self.config.langfuse_secret_key,
                    public_key=self.config.langfuse_public_key,
                    host=self.config.langfuse_host
                )
                self.callbacks.append(callback)
            
            logger.info("🔗 LangFuse integration enabled")
        except Exception as e:
            logger.error(f"❌ LangFuse initialization failed: {e}")
    
    def get_callbacks(self) -> List:
        """Get all LLM callbacks"""
        return self.callbacks
    
    def track_llm_call(self, model: str, provider: str, prompt: str, response: str, 
                      response_time: float, tokens_used: Dict[str, int]):
        """Track LLM API call"""
        if PROMETHEUS_AVAILABLE:
            # Update Prometheus metrics
            self._update_llm_metrics(model, provider, response_time, tokens_used)
        
        # Log LLM call
        logger.info(
            f"🤖 LLM Call - Model: {model}, Provider: {provider}, "
            f"Response Time: {response_time:.2f}s, Tokens: {sum(tokens_used.values())}"
        )
    
    def _update_llm_metrics(self, model: str, provider: str, response_time: float, 
                           tokens_used: Dict[str, int]):
        """Update LLM metrics in Prometheus"""
        # Update response time histogram
        self.metrics.llm_response_time.labels(
            model=model, provider=provider
        ).observe(response_time)
        
        # Update token usage counters
        for token_type, count in tokens_used.items():
            self.metrics.llm_tokens_used.labels(
                model=model, provider=provider, token_type=token_type
            ).inc(count)


class ObservabilityStack:
    """Main observability stack coordinator"""
    
    def __init__(self, config: ObservabilityConfig):
        self.config = config
        self.tracer = None
        self.meter = None
        self.metrics = CustomMetrics()
        self.system_monitor = SystemMonitor(self.metrics)
        self.llm_observer = LLMObserver(config)
        
        # Initialize OpenTelemetry
        self._init_opentelemetry()
        
        # Start Prometheus server if enabled
        if config.prometheus_enabled and PROMETHEUS_AVAILABLE:
            start_http_server(config.prometheus_port)
            logger.info(f"📊 Prometheus metrics server started on port {config.prometheus_port}")
    
    def _init_opentelemetry(self):
        """Initialize OpenTelemetry tracing and metrics"""
        try:
            # Create resource
            resource = Resource.create({
                ResourceAttributes.SERVICE_NAME: self.config.otel_service_name,
                ResourceAttributes.SERVICE_VERSION: self.config.otel_service_version,
            })
            
            # Initialize tracing
            trace.set_tracer_provider(TracerProvider(resource=resource))
            self.tracer = trace.get_tracer(__name__, self.config.otel_service_version)
            
            # Configure trace exporter
            trace_exporter = OTLPSpanExporter(
                endpoint=f"{self.config.otel_exporter_endpoint}/v1/traces"
            )
            trace_processor = BatchSpanProcessor(
                trace_exporter,
                schedule_delay_millis=self.config.otel_export_interval
            )
            trace.get_tracer_provider().add_span_processor(trace_processor)
            
            # Initialize metrics
            metric_reader = PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=f"{self.config.otel_exporter_endpoint}/v1/metrics"
                ),
                export_interval_millis=self.config.otel_export_interval
            )
            self.meter = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader]
            )
            metrics.set_meter_provider(self.meter)
            
            # Instrument libraries
            self._instrument_libraries()
            
            logger.info("🔍 OpenTelemetry initialized")
        
        except Exception as e:
            logger.error(f"❌ OpenTelemetry initialization failed: {e}")
    
    def _instrument_libraries(self):
        """Instrument common libraries for automatic tracing"""
        try:
            # FastAPI instrumentation
            FastAPIInstrumentor().instrument()
            
            # HTTP client instrumentation
            RequestsInstrumentor().instrument()
            AioHttpInstrumentor().instrument()
            
            # Database instrumentation
            AsyncPGInstrumentor().instrument()
            Psycopg2Instrumentor().instrument()
            
            logger.info("🔧 Library instrumentation complete")
        
        except Exception as e:
            logger.error(f"❌ Library instrumentation failed: {e}")
    
    @asynccontextmanager
    async def trace_operation(self, operation_name: str, **attributes) -> AsyncGenerator:
        """Context manager for tracing operations"""
        if not self.tracer:
            yield
            return
        
        with self.tracer.start_as_current_span(operation_name) as span:
            # Add custom attributes
            for key, value in attributes.items():
                span.set_attribute(key, value)
            
            start_time = time.time()
            
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("operation.duration", duration)
    
    def create_span(self, name: str, **attributes):
        """Create a new span"""
        if not self.tracer:
            return None
        
        span = self.tracer.start_span(name)
        for key, value in attributes.items():
            span.set_attribute(key, value)
        return span
    
    def end_span(self, span, status=None, exception=None):
        """End a span"""
        if span:
            if exception:
                span.record_exception(exception)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))
            elif status:
                span.set_status(status)
            span.end()
    
    def get_llm_callbacks(self) -> List:
        """Get LLM callbacks for LangChain integration"""
        return self.llm_observer.get_callbacks()
    
    async def start_monitoring(self):
        """Start all monitoring components"""
        await self.system_monitor.start_monitoring()
        logger.info("📊 Observability stack monitoring started")
    
    async def stop_monitoring(self):
        """Stop all monitoring components"""
        await self.system_monitor.stop_monitoring()
        logger.info("📊 Observability stack monitoring stopped")
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        summary = {
            "timestamp": time.time(),
            "service": {
                "name": self.config.otel_service_name,
                "version": self.config.otel_service_version
            }
        }
        
        # System metrics
        try:
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            summary["system"] = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_gb": memory.used / (1024**3),
                "disk_usage_percent": disk.percent,
                "active_threads": threading.active_count(),
                "active_processes": len(psutil.pids())
            }
        except Exception as e:
            summary["system"] = {"error": str(e)}
        
        # LLM metrics (if Prometheus available)
        if PROMETHEUS_AVAILABLE:
            try:
                from prometheus_client import REGISTRY
                
                # Get current metric values
                metrics_data = {}
                for metric in REGISTRY.collect():
                    if metric.name.startswith('epstein_'):
                        metrics_data[metric.name] = {
                            "type": metric.type,
                            "samples": [
                                {
                                    "name": sample.name,
                                    "labels": sample.labels,
                                    "value": sample.value
                                }
                                for sample in metric.samples
                            ]
                        }
                
                summary["metrics"] = metrics_data
            except Exception as e:
                summary["metrics"] = {"error": str(e)}
        
        return summary


# Global observability stack instance
_observability_stack: Optional[ObservabilityStack] = None


def get_observability_stack() -> ObservabilityStack:
    """Get the global observability stack instance"""
    global _observability_stack
    
    if _observability_stack is None:
        config = ObservabilityConfig(
            otel_service_name=os.getenv("OTEL_SERVICE_NAME", "epstein_files"),
            otel_service_version=os.getenv("OTEL_SERVICE_VERSION", "1.0.0"),
            otel_exporter_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"),
            langsmith_api_key=os.getenv("LANGCHAIN_API_KEY"),
            langsmith_project=os.getenv("LANGCHAIN_PROJECT", "epstein_files"),
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            prometheus_port=int(os.getenv("METRICS_PORT", "8000"))
        )
        
        _observability_stack = ObservabilityStack(config)
    
    return _observability_stack


def trace_function(func: Callable) -> Callable:
    """Decorator for tracing function calls"""
    async def async_wrapper(*args, **kwargs):
        stack = get_observability_stack()
        operation_name = f"{func.__module__}.{func.__name__}"
        
        async with stack.trace_operation(operation_name):
            return await func(*args, **kwargs)
    
    def sync_wrapper(*args, **kwargs):
        stack = get_observability_stack()
        operation_name = f"{func.__module__}.{func.__name__}"
        
        with stack.tracer.start_as_current_span(operation_name):
            return func(*args, **kwargs)
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def track_llm_call(model: str, provider: str):
    """Decorator for tracking LLM calls"""
    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            stack = get_observability_stack()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time
                
                # Extract tokens used (implementation depends on LLM library)
                tokens_used = getattr(result, 'usage', {}) if hasattr(result, 'usage') else {}
                
                stack.llm_observer.track_llm_call(
                    model=model, provider=provider,
                    prompt=str(args[0]) if args else "",
                    response=str(result) if result else "",
                    response_time=response_time,
                    tokens_used=tokens_used
                )
                
                return result
            
            except Exception as e:
                response_time = time.time() - start_time
                stack.llm_observer.track_llm_call(
                    model=model, provider=provider,
                    prompt=str(args[0]) if args else "",
                    response=str(e),
                    response_time=response_time,
                    tokens_used={}
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            stack = get_observability_stack()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                response_time = time.time() - start_time
                
                # Extract tokens used
                tokens_used = getattr(result, 'usage', {}) if hasattr(result, 'usage') else {}
                
                stack.llm_observer.track_llm_call(
                    model=model, provider=provider,
                    prompt=str(args[0]) if args else "",
                    response=str(result) if result else "",
                    response_time=response_time,
                    tokens_used=tokens_used
                )
                
                return result
            
            except Exception as e:
                response_time = time.time() - start_time
                stack.llm_observer.track_llm_call(
                    model=model, provider=provider,
                    prompt=str(args[0]) if args else "",
                    response=str(e),
                    response_time=response_time,
                    tokens_used={}
                )
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


if __name__ == "__main__":
    # Example usage
    import asyncio
    import threading
    
    async def example_usage():
        """Example of using the observability stack"""
        
        # Initialize observability
        stack = get_observability_stack()
        await stack.start_monitoring()
        
        # Example traced operation
        async with stack.trace_operation("example_operation", user_id="test_user"):
            print("🔍 Traced operation in progress...")
            await asyncio.sleep(1)
            print("✅ Traced operation completed")
        
        # Example LLM tracking (if LangChain available)
        if LANGCHAIN_AVAILABLE:
            from langchain.llms import OpenAI
            
            # Wrap LLM call with tracking
            @track_llm_call(model="gpt-3.5-turbo", provider="openai")
            async def call_llm(prompt: str):
                llm = OpenAI(model="gpt-3.5-turbo")
                return await llm.acomplete(prompt)
            
            # Call LLM with tracking
            result = await call_llm("What is the capital of France?")
            print(f"🤖 LLM Response: {result}")
        
        # Get metrics summary
        summary = stack.get_metrics_summary()
        print(f"\n📊 Metrics Summary: {json.dumps(summary, indent=2)}")
        
        # Stop monitoring
        await stack.stop_monitoring()
    
    # Run example
    asyncio.run(example_usage())