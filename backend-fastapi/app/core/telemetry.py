"""
OpenTelemetry integration for distributed tracing and metrics.

This module provides APM (Application Performance Monitoring) capabilities
through OpenTelemetry, supporting both Jaeger and OTLP exporters.
"""
import logging
from typing import Optional
from contextlib import asynccontextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.trace import Status, StatusCode

from app.core.config import settings

logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None
_tracer: Optional[trace.Tracer] = None
_propagator = TraceContextTextMapPropagator()


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


def setup_telemetry(
    service_name: str = "smart-code-assistant",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    jaeger_host: Optional[str] = None,
    jaeger_port: int = 6831,
    sample_rate: float = 1.0,
) -> TracerProvider:
    """
    Setup OpenTelemetry tracing.

    Args:
        service_name: Service name for identification
        service_version: Service version
        otlp_endpoint: OTLP collector endpoint (e.g., http://localhost:4317)
        jaeger_host: Jaeger agent host (for UDP export)
        jaeger_port: Jaeger agent port
        sample_rate: Sampling rate (0.0 to 1.0)

    Returns:
        Configured TracerProvider
    """
    global _tracer_provider

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "service.environment": settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else "development",
    })

    _tracer_provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(f"OTLP exporter configured: {otlp_endpoint}")
        except ImportError:
            logger.warning("OTLP exporter not available, install opentelemetry-exporter-otlp-proto-grpc")

    if jaeger_host:
        try:
            from opentelemetry.exporter.jaeger.proto.grpc import JaegerExporter
            jaeger_exporter = JaegerExporter(
                host=jaeger_host,
                port=jaeger_port,
            )
            _tracer_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info(f"Jaeger exporter configured: {jaeger_host}:{jaeger_port}")
        except ImportError:
            logger.warning("Jaeger exporter not available, install opentelemetry-exporter-jaeger-proto-grpc")

    if not otlp_endpoint and not jaeger_host:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        _tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("Console span exporter configured (no remote exporter specified)")

    trace.set_tracer_provider(_tracer_provider)

    logger.info(f"OpenTelemetry initialized for service: {service_name}")
    return _tracer_provider


def shutdown_telemetry() -> None:
    """Shutdown OpenTelemetry and flush pending spans."""
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()
        logger.info("OpenTelemetry shutdown complete")


@asynccontextmanager
async def traced_operation(
    operation_name: str,
    attributes: Optional[dict] = None,
    record_exception: bool = True,
):
    """
    Context manager for tracing async operations.

    Args:
        operation_name: Name of the operation
        attributes: Optional attributes to add to span
        record_exception: Whether to record exceptions

    Yields:
        The span object

    Example:
        async with traced_operation("database_query", {"db.table": "users"}) as span:
            result = await db.execute(query)
            span.set_attribute("db.rows_affected", result.rowcount)
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(operation_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)

        try:
            yield span
        except Exception as e:
            if record_exception:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def inject_trace_context(headers: dict) -> dict:
    """
    Inject trace context into headers for distributed tracing.

    Args:
        headers: Headers dictionary to inject into

    Returns:
        Headers with trace context
    """
    _propagator.inject(headers)
    return headers


def extract_trace_context(headers: dict) -> Optional[trace.SpanContext]:
    """
    Extract trace context from headers.

    Args:
        headers: Headers dictionary

    Returns:
        SpanContext if present, None otherwise
    """
    ctx = _propagator.extract(headers)
    return trace.get_current_span(ctx).get_span_context()


class TraceableMixin:
    """
    Mixin class for adding tracing capabilities to any class.

    Example:
        class MyService(TraceableMixin):
            async def do_something(self):
                with self.trace("operation") as span:
                    span.set_attribute("custom", "value")
    """

    @property
    def _trace_name(self) -> str:
        return self.__class__.__name__

    def trace(self, operation: str, attributes: Optional[dict] = None):
        """Create a traced span for an operation."""
        tracer = get_tracer()
        span_name = f"{self._trace_name}.{operation}"
        span = tracer.start_as_current_span(span_name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        return span


def trace_function(name: Optional[str] = None, attributes: Optional[dict] = None):
    """
    Decorator for tracing sync/async functions.

    Args:
        name: Span name (defaults to function name)
        attributes: Static attributes to add to span

    Example:
        @trace_function("database_query", {"db.system": "mysql"})
        async def get_user(user_id: int):
            return await db.get(User, user_id)
    """
    def decorator(func):
        import functools
        import asyncio

        span_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = get_tracer()
                with tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = get_tracer()
                with tracer.start_as_current_span(span_name) as span:
                    if attributes:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        raise
            return sync_wrapper

    return decorator
