from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.core.rate_limiter import setup_rate_limiting
from app.core.performance_middleware import setup_performance_monitoring, metrics_collector
from app.core.telemetry import setup_telemetry, shutdown_telemetry
from app.core.alerting import performance_monitor, alert_manager, AlertRule, AlertType, AlertSeverity
from app.core.query_analyzer import query_analyzer
from app.core.sentry import init_sentry
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.projects import router as projects_router
from app.api.code_files import router as code_files_router
from app.api.code_gen import router as code_gen_router
from app.api.agent import router as agent_router
from app.api.documents import router as documents_router
from app.api.versions import router as versions_router
from app.api.user_profile import router as user_profile_router
from app.api.document_parse import router as document_parse_router
from app.api.agents import router as agents_router, conversations_router, training_router
from app.api.code_graph import router as code_graph_router
from app.api.code_analysis import router as code_analysis_router
from app.api.agent_stream import router as agent_stream_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    from app.database import enable_query_monitoring

    # No-op when SENTRY_DSN is unset.
    init_sentry()

    otlp_endpoint = getattr(settings, 'OTLP_ENDPOINT', None)
    jaeger_host = getattr(settings, 'JAEGER_HOST', None)

    setup_telemetry(
        service_name="smart-code-assistant",
        otlp_endpoint=otlp_endpoint,
        jaeger_host=jaeger_host,
    )

    enable_query_monitoring()

    await performance_monitor.start()

    yield

    await performance_monitor.stop()
    shutdown_telemetry()


# Create FastAPI application
app = FastAPI(
    title="Smart Code Assistant API",
    description="AI-powered code generation and review platform",
    version="1.0.0",
    docs_url="/docs" if settings.FASTAPI_ENV == "development" else None,
    redoc_url="/redoc" if settings.FASTAPI_ENV == "development" else None,
    lifespan=lifespan,
)

# Register global exception handlers
register_exception_handlers(app)

# Setup rate limiting
setup_rate_limiting(app)

# Setup performance monitoring
setup_performance_monitoring(app)

# Configure CORS middleware
# 生产环境必须显式配置 CORS_ORIGINS_PROD
cors_origins = settings.CORS_ORIGINS
if settings.is_production and not cors_origins:
    import logging
    logging.warning("⚠️ 生产环境 CORS_ORIGINS_PROD 未配置，所有跨域请求将被拒绝！")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Include routers
app.include_router(health_router, prefix="", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
app.include_router(code_files_router, prefix="/api/v1/code-files", tags=["Code Files"])
app.include_router(code_gen_router, prefix="/api/v1/ai", tags=["AI Code Generation"])
app.include_router(agent_router, prefix="/api/v1/agent", tags=["AI Agent"])
app.include_router(agent_stream_router, prefix="/api/v1/agent", tags=["Agent Stream"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(versions_router, prefix="/api/v1", tags=["Versions"])
app.include_router(user_profile_router, prefix="/api/v1/user", tags=["User Profile"])
app.include_router(document_parse_router, prefix="/api/v1/documents/parse", tags=["Document Parse"])
# Agent system routes
app.include_router(agents_router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(conversations_router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(training_router, prefix="/api/v1/training-tasks", tags=["Training Tasks"])
# Code Graph routes
app.include_router(code_graph_router, prefix="/api/v1/code-graph", tags=["Code Graph"])
# Code Analysis routes (统一代码分析接口)
app.include_router(code_analysis_router, prefix="/api/v1/code-analysis", tags=["Code Analysis"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Smart Code Assistant API",
        "version": "1.0.0",
        "docs": "/docs" if settings.FASTAPI_ENV == "development" else None
    }


@app.get("/api/v1")
async def api_v1():
    """API v1 endpoint."""
    return {
        "message": "Smart Code Assistant API v1",
        "version": "1.0.0"
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint.

    Returns performance metrics in Prometheus text format.
    """
    return Response(
        content=metrics_collector.get_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@app.get("/api/v1/performance/stats")
async def performance_stats(endpoint: str = None):
    """
    Get performance statistics.

    Args:
        endpoint: Optional endpoint filter

    Returns:
        Aggregated performance statistics
    """
    return metrics_collector.get_stats(endpoint)


@app.get("/api/v1/performance/alerts")
async def get_alerts(
    limit: int = 100,
    severity: str = None,
):
    """
    Get performance alert history.

    Args:
        limit: Maximum number of alerts to return
        severity: Filter by severity (info, warning, error, critical)

    Returns:
        List of alerts
    """
    from app.core.alerting import AlertSeverity

    severity_filter = None
    if severity:
        try:
            severity_filter = AlertSeverity(severity.lower())
        except ValueError:
            pass

    return alert_manager.get_alert_history(limit, severity_filter)


@app.get("/api/v1/performance/alerts/stats")
async def get_alert_stats():
    """Get alert statistics."""
    return alert_manager.get_alert_stats()


@app.post("/api/v1/performance/alerts/rules")
async def add_alert_rule(
    name: str,
    alert_type: str,
    threshold: float,
    window_seconds: int = 60,
    severity: str = "warning",
    description: str = "",
):
    """
    Add a new alert rule.

    Args:
        name: Rule name
        alert_type: Type of alert (high_latency, high_error_rate, etc.)
        threshold: Threshold value
        window_seconds: Time window in seconds
        severity: Alert severity (info, warning, error, critical)
        description: Rule description
    """
    try:
        alert_type_enum = AlertType(alert_type)
        severity_enum = AlertSeverity(severity.lower())
    except ValueError as e:
        return {"error": f"Invalid alert_type or severity: {e}"}

    rule = AlertRule(
        name=name,
        alert_type=alert_type_enum,
        threshold=threshold,
        window_seconds=window_seconds,
        severity=severity_enum,
        description=description,
    )
    alert_manager.add_rule(rule)
    return {"message": f"Alert rule '{name}' added", "rule": rule.__dict__}


@app.delete("/api/v1/performance/alerts/rules/{rule_name}")
async def remove_alert_rule(rule_name: str):
    """Remove an alert rule."""
    if alert_manager.remove_rule(rule_name):
        return {"message": f"Alert rule '{rule_name}' removed"}
    return {"error": f"Alert rule '{rule_name}' not found"}


@app.get("/api/v1/performance/queries/stats")
async def get_query_stats():
    """Get database query statistics."""
    return query_analyzer.get_stats()


@app.get("/api/v1/performance/queries/n-plus-one")
async def get_n_plus_one_candidates():
    """Get potential N+1 query patterns."""
    return query_analyzer.get_n_plus_one_candidates()


@app.get("/api/v1/performance/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    from app.core.cache import global_cache_manager
    return global_cache_manager.get_stats()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.FASTAPI_HOST,
        port=settings.FASTAPI_PORT,
        reload=settings.FASTAPI_ENV == "development",
        log_level="info"
    )
