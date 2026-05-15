"""
Performance monitoring middleware for API metrics collection.

Automatically collects request/response metrics and stores them for analysis.
"""
import time
import logging
import json
from typing import Optional, Callable, List
from threading import Lock
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Thread-safe in-memory metrics collector.

    Collects and aggregates performance metrics in memory with periodic
    persistence to database. Uses sliding window for real-time stats.
    """

    def __init__(self, window_seconds: int = 60):
        self._metrics: List[dict] = []
        self._lock = Lock()
        self._window_seconds = window_seconds
        self._endpoint_stats: dict = defaultdict(lambda: {
            "count": 0,
            "total_time": 0,
            "errors": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "response_times": [],
        })
        self._pending_db_writes: List[dict] = []
        self._max_pending = 100

    def record(
        self,
        endpoint: str,
        method: str,
        response_time_ms: float,
        status_code: int,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
        user_id: Optional[int] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Record a request metric.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            response_time_ms: Response time in milliseconds
            status_code: HTTP status code
            request_size: Request body size in bytes
            response_size: Response body size in bytes
            user_id: User ID if authenticated
            client_ip: Client IP address
            user_agent: Client user agent
            error_message: Error message if failed
        """
        metric = {
            "metric_type": "api_request",
            "endpoint": endpoint,
            "method": method,
            "response_time_ms": response_time_ms,
            "status_code": status_code,
            "request_size": request_size,
            "response_size": response_size,
            "user_id": user_id,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "error_message": error_message,
            "created_at": datetime.utcnow().isoformat(),
        }

        with self._lock:
            self._metrics.append(metric)
            self._cleanup_old_metrics()

            stats = self._endpoint_stats[endpoint]
            stats["count"] += 1
            stats["total_time"] += response_time_ms
            stats["min_time"] = min(stats["min_time"], response_time_ms)
            stats["max_time"] = max(stats["max_time"], response_time_ms)
            stats["response_times"].append(response_time_ms)
            if status_code >= 400:
                stats["errors"] += 1

            self._pending_db_writes.append(metric)
            if len(self._pending_db_writes) >= self._max_pending:
                self._flush_to_db()

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than the window."""
        cutoff = datetime.utcnow() - timedelta(seconds=self._window_seconds)
        self._metrics = [
            m for m in self._metrics
            if datetime.fromisoformat(m["created_at"]) > cutoff
        ]

        for endpoint in self._endpoint_stats:
            stats = self._endpoint_stats[endpoint]
            stats["response_times"] = [
                t for t in stats["response_times"]
            ][-1000:]

    def _flush_to_db(self) -> None:
        """Flush pending metrics to database."""
        if not self._pending_db_writes:
            return

        try:
            from app.database import AsyncSessionLocal
            from app.models.performance import PerformanceMetric
            import asyncio

            async def write_metrics():
                async with AsyncSessionLocal() as session:
                    for metric_data in self._pending_db_writes:
                        metric = PerformanceMetric(
                            metric_type=metric_data["metric_type"],
                            endpoint=metric_data["endpoint"],
                            method=metric_data["method"],
                            response_time_ms=metric_data["response_time_ms"],
                            status_code=metric_data["status_code"],
                            request_size=metric_data.get("request_size"),
                            response_size=metric_data.get("response_size"),
                            user_id=metric_data.get("user_id"),
                            client_ip=metric_data.get("client_ip"),
                            user_agent=metric_data.get("user_agent"),
                            error_message=metric_data.get("error_message"),
                        )
                        session.add(metric)
                    await session.commit()

            try:
                loop = asyncio.get_running_loop()
                asyncio.ensure_future(write_metrics())
            except RuntimeError:
                asyncio.run(write_metrics())

            self._pending_db_writes.clear()
            logger.debug(f"Flushed {len(self._pending_db_writes)} metrics to database")
        except Exception as e:
            logger.warning(f"Failed to flush metrics to database: {e}")

    def get_stats(self, endpoint: Optional[str] = None) -> dict:
        """
        Get aggregated statistics.

        Args:
            endpoint: Optional endpoint filter

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            if endpoint:
                return self._get_endpoint_stats(endpoint)

            all_stats = {}
            for ep, stats in self._endpoint_stats.items():
                all_stats[ep] = self._calculate_percentiles(stats)
            return all_stats

    def _get_endpoint_stats(self, endpoint: str) -> dict:
        """Calculate statistics for a single endpoint."""
        stats = self._endpoint_stats.get(endpoint, {})
        if not stats or stats["count"] == 0:
            return {"error": "No data for endpoint"}

        return self._calculate_percentiles(stats)

    def _calculate_percentiles(self, stats: dict) -> dict:
        """Calculate percentile statistics."""
        if not stats["response_times"]:
            return {"error": "No response time data"}

        times = sorted(stats["response_times"])
        count = len(times)

        def percentile(p: float) -> float:
            idx = int(count * p / 100)
            idx = min(idx, count - 1)
            return times[idx]

        return {
            "count": stats["count"],
            "errors": stats["errors"],
            "error_rate": stats["errors"] / stats["count"] * 100 if stats["count"] > 0 else 0,
            "avg_ms": stats["total_time"] / stats["count"] if stats["count"] > 0 else 0,
            "min_ms": stats["min_time"] if stats["min_time"] != float('inf') else 0,
            "max_ms": stats["max_time"],
            "p50_ms": percentile(50),
            "p95_ms": percentile(95),
            "p99_ms": percentile(99),
        }

    def get_prometheus_metrics(self) -> str:
        """
        Generate Prometheus-compatible metrics output.

        Returns:
            String in Prometheus text format
        """
        lines = []
        lines.append("# HELP http_request_duration_ms HTTP request duration in milliseconds")
        lines.append("# TYPE http_request_duration_ms summary")

        with self._lock:
            for endpoint, stats in self._endpoint_stats.items():
                if stats["count"] == 0:
                    continue

                labels = f'endpoint="{endpoint}"'
                percentiles = self._calculate_percentiles(stats)

                lines.append(f'http_request_duration_ms{{quantile="0.5",{labels}}} {percentiles["p50_ms"]:.2f}')
                lines.append(f'http_request_duration_ms{{quantile="0.95",{labels}}} {percentiles["p95_ms"]:.2f}')
                lines.append(f'http_request_duration_ms{{quantile="0.99",{labels}}} {percentiles["p99_ms"]:.2f}')
                lines.append(f'http_request_duration_ms_sum{{{labels}}} {stats["total_time"]:.2f}')
                lines.append(f'http_request_duration_ms_count{{{labels}}} {stats["count"]}')

        lines.append("")
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")

        with self._lock:
            for endpoint, stats in self._endpoint_stats.items():
                labels = f'endpoint="{endpoint}"'
                lines.append(f'http_requests_total{{{labels}}} {stats["count"]}')
                if stats["errors"] > 0:
                    lines.append(f'http_request_errors_total{{{labels}}} {stats["errors"]}')

        return "\n".join(lines)


metrics_collector = MetricsCollector()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic performance monitoring.

    Records request/response metrics including:
    - Response time
    - Request/response sizes
    - Status codes
    - User information (if authenticated)
    """

    SKIP_PATHS = {
        "/",
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    def __init__(self, app: ASGIApp, collector: Optional[MetricsCollector] = None):
        super().__init__(app)
        self.collector = collector or metrics_collector

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        path = request.url.path

        if path in self.SKIP_PATHS or path.startswith("/static/"):
            return await call_next(request)

        start_time = time.perf_counter()
        error_message = None
        response = None

        try:
            response = await call_next(request)
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            end_time = time.perf_counter()
            response_time_ms = (end_time - start_time) * 1000

            request_size = None
            if request.headers.get("content-length"):
                try:
                    request_size = int(request.headers["content-length"])
                except ValueError:
                    pass

            response_size = None
            if response and hasattr(response, "headers"):
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        response_size = int(content_length)
                    except ValueError:
                        pass

            user_id = None
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent", "")[:500]

            self.collector.record(
                endpoint=path,
                method=request.method,
                response_time_ms=response_time_ms,
                status_code=response.status_code if response else 500,
                request_size=request_size,
                response_size=response_size,
                user_id=user_id,
                client_ip=client_ip,
                user_agent=user_agent,
                error_message=error_message,
            )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


def setup_performance_monitoring(app) -> None:
    """Setup performance monitoring middleware for the FastAPI application."""
    app.add_middleware(PerformanceMiddleware, collector=metrics_collector)
    logger.info("Performance monitoring middleware enabled")
