"""
Tests for the SQL query analyzer (slow query + N+1 detection).
"""
from datetime import timedelta

import pytest

from app.core.query_analyzer import QueryAnalyzer


@pytest.fixture
def analyzer():
    # tight thresholds make assertions deterministic
    return QueryAnalyzer(
        slow_query_threshold_ms=100,
        n_plus_one_threshold=3,
        sample_window_seconds=300,
    )


class TestExtractPattern:
    def test_pattern_normalises_numbers(self, analyzer):
        a = analyzer._extract_pattern("SELECT * FROM users WHERE id = 1")
        b = analyzer._extract_pattern("SELECT * FROM users WHERE id = 12345")
        assert a == b

    def test_pattern_normalises_string_literals(self, analyzer):
        a = analyzer._extract_pattern("SELECT * FROM u WHERE n = 'a'")
        b = analyzer._extract_pattern("SELECT * FROM u WHERE n = 'b'")
        assert a == b

    def test_pattern_collapses_whitespace(self, analyzer):
        a = analyzer._extract_pattern("SELECT   *  FROM\tt")
        b = analyzer._extract_pattern("SELECT * FROM t")
        assert a == b


class TestRecordQuery:
    def test_fast_query_produces_no_alerts(self, analyzer):
        alerts = analyzer.record_query("SELECT 1", duration_ms=5)
        assert alerts is None

    def test_slow_query_emits_alert(self, analyzer):
        alerts = analyzer.record_query("SELECT slow()", duration_ms=250)
        assert alerts and alerts[0]["type"] == "slow_query"
        assert alerts[0]["duration_ms"] == 250
        assert alerts[0]["threshold_ms"] == 100

    def test_n_plus_one_detected_on_repeat_pattern(self, analyzer):
        for i in range(3):
            alerts = analyzer.record_query(
                f"SELECT * FROM u WHERE id = {i}",
                duration_ms=5,
                session_id="s1",
            )
        # the third call should trip n_plus_one
        assert alerts is not None
        assert any(a["type"] == "n_plus_one" for a in alerts)

    def test_n_plus_one_not_triggered_across_sessions(self, analyzer):
        for i in range(5):
            alerts = analyzer.record_query(
                f"SELECT * FROM u WHERE id = {i}",
                duration_ms=5,
                session_id=f"different-session-{i}",
            )
            assert alerts is None or all(a["type"] != "n_plus_one" for a in alerts)


class TestStats:
    def test_stats_empty_initially(self, analyzer):
        s = analyzer.get_stats()
        assert s["total_queries"] == 0
        assert s["slow_queries"] == 0

    def test_stats_aggregate_after_queries(self, analyzer):
        analyzer.record_query("SELECT 1", duration_ms=10)
        analyzer.record_query("SELECT 2", duration_ms=200)
        analyzer.record_query("SELECT 3", duration_ms=300)

        s = analyzer.get_stats()
        assert s["total_queries"] == 3
        assert s["slow_queries"] == 2
        assert s["avg_duration_ms"] == round((10 + 200 + 300) / 3, 2)
        assert s["slow_query_threshold_ms"] == 100
        assert "top_queries" in s
        assert "recent_slow_queries" in s


class TestNPlusOneCandidates:
    def test_returns_patterns_above_threshold(self, analyzer):
        for i in range(5):
            analyzer.record_query(f"SELECT * FROM t WHERE id = {i}", duration_ms=5)
        candidates = analyzer.get_n_plus_one_candidates()
        assert candidates
        assert candidates[0]["count"] >= 3
        assert "recommendation" in candidates[0]

    def test_returns_empty_when_below_threshold(self, analyzer):
        analyzer.record_query("SELECT 1", duration_ms=5)
        assert analyzer.get_n_plus_one_candidates() == []


class TestCleanup:
    def test_cleanup_drops_aged_queries(self, analyzer):
        analyzer.record_query("SELECT 1", duration_ms=5)
        assert len(analyzer._queries) == 1
        # Manually push timestamp into the past beyond the window
        analyzer._queries[0].timestamp -= timedelta(seconds=400)
        analyzer._cleanup_old_queries()
        assert analyzer._queries == []
