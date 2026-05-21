"""
Tests for MetricsCollector + PerformanceMiddleware path-skip logic.

DB flush is patched out so tests stay pure in-memory.
"""
from unittest.mock import patch, MagicMock

import pytest

from app.core.performance_middleware import MetricsCollector, PerformanceMiddleware


@pytest.fixture
def collector():
    """Isolated collector with DB flush disabled."""
    c = MetricsCollector(window_seconds=60)
    # Stub the DB flush so we never touch the real engine.
    c._flush_to_db = lambda: None
    return c


# ----- MetricsCollector.record + get_stats -----

class TestRecordAndStats:
    def test_no_data_yields_no_stats(self, collector):
        assert collector.get_stats() == {}

    def test_single_record_populates_endpoint_stats(self, collector):
        collector.record("/x", "GET", response_time_ms=50, status_code=200)
        stats = collector.get_stats("/x")
        assert stats["count"] == 1
        assert stats["errors"] == 0
        assert stats["avg_ms"] == 50
        assert stats["p50_ms"] == 50

    def test_error_status_increments_errors(self, collector):
        for code in (200, 500, 503):
            collector.record("/x", "GET", response_time_ms=10, status_code=code)
        stats = collector.get_stats("/x")
        assert stats["count"] == 3
        assert stats["errors"] == 2
        # 2/3 ≈ 66.67%
        assert round(stats["error_rate"], 1) == round(2 / 3 * 100, 1)

    def test_percentiles_ordered(self, collector):
        for i in range(1, 101):
            collector.record("/x", "GET", response_time_ms=float(i), status_code=200)
        stats = collector.get_stats("/x")
        assert stats["p50_ms"] <= stats["p95_ms"] <= stats["p99_ms"]
        assert stats["min_ms"] == 1
        assert stats["max_ms"] == 100

    def test_get_stats_for_unknown_endpoint(self, collector):
        result = collector.get_stats("/missing")
        assert result == {"error": "No data for endpoint"}


# ----- Prometheus serialiser -----

class TestPrometheusFormat:
    def test_empty_collector_returns_header_only(self, collector):
        out = collector.get_prometheus_metrics()
        # Header lines are always present
        assert "# HELP http_request_duration_ms" in out
        assert "# TYPE http_request_duration_ms summary" in out
        assert "# HELP http_requests_total" in out

    def test_records_emit_quantile_lines(self, collector):
        collector.record("/api", "GET", response_time_ms=5, status_code=200)
        collector.record("/api", "GET", response_time_ms=15, status_code=500)
        out = collector.get_prometheus_metrics()
        assert 'http_request_duration_ms{quantile="0.5",endpoint="/api"}' in out
        assert 'http_requests_total{endpoint="/api"} 2' in out
        assert 'http_request_errors_total{endpoint="/api"} 1' in out


# ----- Middleware skip-path logic -----

class TestMiddlewareSkipPaths:
    @pytest.fixture
    def middleware(self):
        return PerformanceMiddleware(app=MagicMock())

    def test_skip_paths_set(self, middleware):
        for p in ["/", "/health", "/metrics", "/docs", "/redoc", "/openapi.json"]:
            assert p in middleware.SKIP_PATHS

    def test_get_client_ip_prefers_forwarded_for(self, middleware):
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.1, 10.0.0.5"}
        request.client = MagicMock(host="127.0.0.1")
        assert middleware._get_client_ip(request) == "203.0.113.1"

    def test_get_client_ip_falls_back_to_request_client(self, middleware):
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock(host="198.51.100.5")
        assert middleware._get_client_ip(request) == "198.51.100.5"

    def test_get_client_ip_unknown_when_no_client(self, middleware):
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert middleware._get_client_ip(request) == "unknown"
