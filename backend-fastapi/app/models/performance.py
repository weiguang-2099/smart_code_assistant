"""
Performance monitoring models for API metrics collection.
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from app.database import Base


class MetricType(str, Enum):
    """Metric type enum."""
    API_REQUEST = "api_request"
    DB_QUERY = "db_query"
    CACHE_HIT = "cache_hit"
    LLM_CALL = "llm_call"
    TOOL_EXECUTION = "tool_execution"


class PerformanceMetric(Base):
    """
    Performance metric model for storing API and system performance data.

    Attributes:
        id: Primary key
        metric_type: Type of metric (api_request, db_query, etc.)
        endpoint: API endpoint path (e.g., /api/v1/agent/chat)
        method: HTTP method (GET, POST, etc.)
        response_time_ms: Response time in milliseconds
        status_code: HTTP status code
        request_size: Request body size in bytes
        response_size: Response body size in bytes
        user_id: User ID (if authenticated)
        client_ip: Client IP address
        user_agent: Client user agent
        error_message: Error message if request failed
        meta_data: Additional metadata (JSON)
        created_at: Timestamp when metric was recorded
    """

    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    metric_type = Column(String(50), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    response_time_ms = Column(Float, nullable=False, index=True)
    status_code = Column(Integer, nullable=False, index=True)
    request_size = Column(Integer, nullable=True)
    response_size = Column(Integer, nullable=True)
    user_id = Column(Integer, nullable=True, index=True)
    client_ip = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    error_message = Column(Text, nullable=True)
    meta_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index('ix_performance_metrics_endpoint_created', 'endpoint', 'created_at'),
        Index('ix_performance_metrics_type_created', 'metric_type', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<PerformanceMetric(id={self.id}, endpoint='{self.endpoint}', response_time_ms={self.response_time_ms})>"


class PerformanceBaseline(Base):
    """
    Performance baseline model for storing baseline metrics.

    Used to track expected performance levels and detect regressions.

    Attributes:
        id: Primary key
        endpoint: API endpoint path
        method: HTTP method
        p50_ms: 50th percentile response time (median)
        p95_ms: 95th percentile response time
        p99_ms: 99th percentile response time
        avg_ms: Average response time
        min_ms: Minimum response time
        max_ms: Maximum response time
        sample_count: Number of samples used for baseline
        period_start: Start of baseline period
        period_end: End of baseline period
        created_at: When baseline was calculated
        updated_at: When baseline was last updated
    """

    __tablename__ = "performance_baselines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    endpoint = Column(String(255), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    p50_ms = Column(Float, nullable=False)
    p95_ms = Column(Float, nullable=False)
    p99_ms = Column(Float, nullable=False)
    avg_ms = Column(Float, nullable=False)
    min_ms = Column(Float, nullable=False)
    max_ms = Column(Float, nullable=False)
    sample_count = Column(Integer, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('ix_performance_baselines_endpoint_method', 'endpoint', 'method', unique=True),
    )

    def __repr__(self) -> str:
        return f"<PerformanceBaseline(endpoint='{self.endpoint}', p95_ms={self.p95_ms})>"
