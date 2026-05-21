"""
Tests for the alert manager + alert-rule + performance monitor lifecycle.
"""
from datetime import datetime, timedelta

import asyncio
import pytest

from app.core.alerting import (
    Alert,
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertType,
    PerformanceMonitor,
    log_notification,
)


@pytest.fixture
def manager():
    """
    Fresh manager with deep-copied default rules.

    AlertManager.__init__ stores references to the shared DEFAULT_RULES list,
    so mutating .enabled on one manager poisons every other test that touches
    the same rule. Deep-copy the rule objects to break the aliasing.
    """
    import copy
    m = AlertManager()
    m.rules = {name: copy.deepcopy(rule) for name, rule in m.rules.items()}
    return m


# ----- Alert dataclass -----

class TestAlertSerialisation:
    def test_to_dict_round_trip(self):
        alert = Alert(
            rule_name="r1",
            alert_type=AlertType.HIGH_LATENCY,
            severity=AlertSeverity.WARNING,
            message="slow",
            value=600.0,
            threshold=500.0,
            endpoint="/x",
        )
        d = alert.to_dict()
        assert d["rule_name"] == "r1"
        assert d["alert_type"] == "high_latency"
        assert d["severity"] == "warning"
        assert d["value"] == 600.0
        assert d["endpoint"] == "/x"
        # iso timestamp present
        datetime.fromisoformat(d["timestamp"])


# ----- AlertManager rule management -----

class TestRuleManagement:
    def test_default_rules_are_loaded(self, manager):
        # default ruleset names
        assert "p95_latency_high" in manager.rules
        assert "error_rate_high" in manager.rules

    def test_add_rule_inserts_or_updates(self, manager):
        rule = AlertRule(name="custom", alert_type=AlertType.SLOW_ENDPOINT, threshold=200.0)
        manager.add_rule(rule)
        assert manager.rules["custom"] is rule

    def test_remove_existing_rule_returns_true(self, manager):
        manager.add_rule(AlertRule(name="x", alert_type=AlertType.SLOW_ENDPOINT, threshold=1))
        assert manager.remove_rule("x") is True
        assert "x" not in manager.rules

    def test_remove_missing_rule_returns_false(self, manager):
        assert manager.remove_rule("nope") is False


# ----- check_and_alert -----

class TestCheckAndAlert:
    def test_latency_under_threshold_no_alerts(self, manager):
        alerts = manager.check_and_alert({"p95_ms": 10, "error_rate": 0})
        assert alerts == []

    def test_latency_above_threshold_triggers_warning(self, manager):
        alerts = manager.check_and_alert({"p95_ms": 600, "error_rate": 0})
        names = [a.rule_name for a in alerts]
        assert "p95_latency_high" in names

    def test_high_latency_above_critical_threshold(self, manager):
        alerts = manager.check_and_alert({"p95_ms": 1500, "error_rate": 0})
        severities = {a.severity for a in alerts}
        assert AlertSeverity.CRITICAL in severities

    def test_disabled_rule_does_not_fire(self, manager):
        manager.rules["p95_latency_high"].enabled = False
        alerts = manager.check_and_alert({"p95_ms": 600})
        assert all(a.rule_name != "p95_latency_high" for a in alerts)

    def test_cooldown_suppresses_repeat_alerts(self, manager):
        # First fire
        alerts1 = manager.check_and_alert({"p95_ms": 600})
        assert any(a.rule_name == "p95_latency_high" for a in alerts1)
        # Immediately again - cooldown should suppress
        alerts2 = manager.check_and_alert({"p95_ms": 600})
        assert all(a.rule_name != "p95_latency_high" for a in alerts2)

    def test_cooldown_expires_after_window(self, manager):
        alerts = manager.check_and_alert({"p95_ms": 600})
        assert alerts
        # backdate the last alert time beyond cooldown
        rule = manager.rules["p95_latency_high"]
        manager._last_alert_time["p95_latency_high"] = (
            datetime.utcnow() - timedelta(seconds=rule.cooldown_seconds + 1)
        )
        alerts2 = manager.check_and_alert({"p95_ms": 700})
        assert any(a.rule_name == "p95_latency_high" for a in alerts2)


# ----- Notification channels -----

class TestNotifications:
    def test_added_channel_receives_alerts(self, manager):
        received = []
        manager.add_notification_channel(received.append)
        manager.check_and_alert({"p95_ms": 600})
        assert len(received) >= 1
        assert isinstance(received[0], Alert)

    def test_broken_channel_does_not_kill_dispatch(self, manager):
        good_called = []

        def bad(_):
            raise RuntimeError("nope")

        manager.add_notification_channel(bad)
        manager.add_notification_channel(good_called.append)

        manager.check_and_alert({"p95_ms": 700})
        assert len(good_called) >= 1   # still got delivered

    def test_log_notification_runs_without_error(self):
        log_notification(Alert(
            rule_name="x",
            alert_type=AlertType.HIGH_LATENCY,
            severity=AlertSeverity.INFO,
            message="m", value=1.0, threshold=0.0,
        ))


# ----- History + stats -----

class TestHistoryAndStats:
    def test_history_returns_dict_view(self, manager):
        manager.check_and_alert({"p95_ms": 600})
        hist = manager.get_alert_history()
        assert hist
        assert hist[0]["rule_name"] == "p95_latency_high"

    def test_history_severity_filter(self, manager):
        manager.check_and_alert({"p95_ms": 1500})  # triggers both warning and critical
        critical = manager.get_alert_history(severity=AlertSeverity.CRITICAL)
        assert all(a["severity"] == "critical" for a in critical)

    def test_stats_aggregate(self, manager):
        manager.check_and_alert({"p95_ms": 600})
        stats = manager.get_alert_stats()
        assert stats["total_alerts"] >= 1
        assert "counts_by_rule" in stats


# ----- PerformanceMonitor lifecycle (no real loop) -----

class TestPerformanceMonitorLifecycle:
    @pytest.mark.asyncio
    async def test_start_then_stop_cleanly(self):
        mon = PerformanceMonitor(check_interval_seconds=60)
        await mon.start()
        # immediately stop - should not hang or raise
        await asyncio.sleep(0)
        await mon.stop()
        assert mon._running is False

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self):
        mon = PerformanceMonitor(check_interval_seconds=60)
        await mon.start()
        original_task = mon._task
        await mon.start()  # second call should be a no-op
        assert mon._task is original_task
        await mon.stop()
