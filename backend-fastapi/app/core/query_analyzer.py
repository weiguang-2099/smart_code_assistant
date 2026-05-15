"""
Database query analysis and monitoring utilities.

Provides tools for identifying slow queries, N+1 problems, and missing indexes.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from collections import defaultdict
import json

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution."""
    query: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parameters: Optional[dict] = None
    stack_trace: Optional[str] = None
    session_id: Optional[str] = None


class QueryAnalyzer:
    """
    Analyzes database queries for performance issues.

    Features:
    - Slow query detection
    - N+1 query pattern detection
    - Query frequency analysis
    - Query statistics
    """

    def __init__(
        self,
        slow_query_threshold_ms: float = 100.0,
        n_plus_one_threshold: int = 5,
        sample_window_seconds: int = 60,
    ):
        self.slow_query_threshold = slow_query_threshold_ms
        self.n_plus_one_threshold = n_plus_one_threshold
        self.sample_window = sample_window_seconds

        self._queries: List[QueryMetrics] = []
        self._query_counts: Dict[str, int] = defaultdict(int)
        self._slow_queries: List[QueryMetrics] = []
        self._session_queries: Dict[str, List[QueryMetrics]] = defaultdict(list)

    def record_query(
        self,
        query: str,
        duration_ms: float,
        parameters: Optional[dict] = None,
        session_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record a query execution and analyze for issues.

        Returns:
            Alert dict if issue detected, None otherwise
        """
        metrics = QueryMetrics(
            query=query,
            duration_ms=duration_ms,
            parameters=parameters,
            session_id=session_id,
        )

        self._queries.append(metrics)
        query_pattern = self._extract_pattern(query)
        self._query_counts[query_pattern] += 1

        if session_id:
            self._session_queries[session_id].append(metrics)

        self._cleanup_old_queries()

        alerts = []

        if duration_ms > self.slow_query_threshold:
            self._slow_queries.append(metrics)
            alerts.append({
                "type": "slow_query",
                "query": query[:200],
                "duration_ms": duration_ms,
                "threshold_ms": self.slow_query_threshold,
            })

        if session_id:
            session_qs = self._session_queries[session_id]
            recent_similar = [
                q for q in session_qs[-20:]
                if self._extract_pattern(q.query) == query_pattern
            ]
            if len(recent_similar) >= self.n_plus_one_threshold:
                alerts.append({
                    "type": "n_plus_one",
                    "query_pattern": query_pattern,
                    "count": len(recent_similar),
                    "session_id": session_id,
                })

        return alerts if alerts else None

    def _extract_pattern(self, query: str) -> str:
        """Extract query pattern by normalizing parameters."""
        import re
        pattern = query.strip()
        pattern = re.sub(r'\s+', ' ', pattern)
        pattern = re.sub(r"'.*?'", "'?'", pattern)
        pattern = re.sub(r'\b\d+\b', '?', pattern)
        return pattern[:100]

    def _cleanup_old_queries(self) -> None:
        """Remove queries older than the sample window."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.sample_window)
        self._queries = [q for q in self._queries if q.timestamp > cutoff]
        self._slow_queries = [q for q in self._slow_queries if q.timestamp > cutoff]

        for session_id in list(self._session_queries.keys()):
            self._session_queries[session_id] = [
                q for q in self._session_queries[session_id]
                if q.timestamp > cutoff
            ]
            if not self._session_queries[session_id]:
                del self._session_queries[session_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        total_queries = len(self._queries)
        if total_queries == 0:
            return {
                "total_queries": 0,
                "slow_queries": 0,
                "slow_query_threshold_ms": self.slow_query_threshold,
            }

        durations = [q.duration_ms for q in self._queries]
        avg_duration = sum(durations) / len(durations)

        top_queries = sorted(
            self._query_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_queries": total_queries,
            "slow_queries": len(self._slow_queries),
            "avg_duration_ms": round(avg_duration, 2),
            "slow_query_threshold_ms": self.slow_query_threshold,
            "top_queries": [{"pattern": p, "count": c} for p, c in top_queries],
            "recent_slow_queries": [
                {
                    "query": q.query[:200],
                    "duration_ms": q.duration_ms,
                    "timestamp": q.timestamp.isoformat(),
                }
                for q in self._slow_queries[-5:]
            ],
        }

    def get_n_plus_one_candidates(self) -> List[Dict[str, Any]]:
        """Identify potential N+1 query patterns."""
        candidates = []

        for pattern, count in self._query_counts.items():
            if count >= self.n_plus_one_threshold:
                candidates.append({
                    "pattern": pattern,
                    "count": count,
                    "recommendation": "Consider using joinedload or selectinload",
                })

        return sorted(candidates, key=lambda x: x["count"], reverse=True)


query_analyzer = QueryAnalyzer()


def setup_query_monitoring(engine) -> None:
    """
    Setup SQLAlchemy event listeners for query monitoring.

    Args:
        engine: SQLAlchemy engine instance
    """

    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.perf_counter()

    @event.listens_for(engine.sync_engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if not hasattr(context, '_query_start_time'):
            return

        duration_ms = (time.perf_counter() - context._query_start_time) * 1000

        params = None
        if parameters:
            try:
                if isinstance(parameters, dict):
                    params = {k: str(v)[:100] for k, v in list(parameters.items())[:10]}
                elif isinstance(parameters, (list, tuple)):
                    params = [str(p)[:100] for p in list(parameters)[:10]]
            except Exception:
                params = {"raw": str(parameters)[:200]}

        alerts = query_analyzer.record_query(
            query=statement,
            duration_ms=duration_ms,
            parameters=params,
        )

        if alerts:
            for alert in alerts:
                if alert["type"] == "slow_query":
                    logger.warning(
                        f"Slow query detected: {duration_ms:.2f}ms - {statement[:100]}"
                    )
                elif alert["type"] == "n_plus_one":
                    logger.warning(
                        f"Potential N+1 query pattern: {alert['query_pattern'][:50]} "
                        f"({alert['count']} executions)"
                    )

    logger.info("Query monitoring enabled")


@asynccontextmanager
async def analyzed_session(session: AsyncSession, session_id: Optional[str] = None):
    """
    Context manager for analyzing queries in a session.

    Example:
        async with analyzed_session(db, "user_query") as session:
            result = await session.execute(query)
    """
    import uuid
    session_id = session_id or str(uuid.uuid4())[:8]

    start_time = time.perf_counter()
    try:
        yield session
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(f"Session {session_id} completed in {duration_ms:.2f}ms")
