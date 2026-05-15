"""
Performance alerting system.

Monitors performance metrics and triggers alerts when thresholds are exceeded.
Supports multiple notification channels (logging, email, webhook).
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Callable, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Alert type enum."""
    HIGH_LATENCY = "high_latency"
    HIGH_ERROR_RATE = "high_error_rate"
    SLOW_ENDPOINT = "slow_endpoint"
    MEMORY_HIGH = "memory_high"
    CACHE_MISS_HIGH = "cache_miss_high"
    BASELINE_DEVIATION = "baseline_deviation"


@dataclass
class AlertRule:
    """Alert rule configuration."""
    name: str
    alert_type: AlertType
    threshold: float
    window_seconds: int = 60
    min_samples: int = 5
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    cooldown_seconds: int = 300
    description: str = ""


@dataclass
class Alert:
    """Alert instance."""
    rule_name: str
    alert_type: AlertType
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    endpoint: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "value": self.value,
            "threshold": self.threshold,
            "endpoint": self.endpoint,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class AlertManager:
    """
    Manages performance alerts and notifications.

    Features:
    - Configurable alert rules with thresholds
    - Cooldown periods to prevent alert spam
    - Multiple notification channels
    - Alert history and statistics
    """

    DEFAULT_RULES = [
        AlertRule(
            name="p95_latency_high",
            alert_type=AlertType.HIGH_LATENCY,
            threshold=500.0,
            window_seconds=60,
            severity=AlertSeverity.WARNING,
            description="P95 response time exceeds 500ms",
        ),
        AlertRule(
            name="p95_latency_critical",
            alert_type=AlertType.HIGH_LATENCY,
            threshold=1000.0,
            window_seconds=60,
            severity=AlertSeverity.CRITICAL,
            description="P95 response time exceeds 1s",
        ),
        AlertRule(
            name="error_rate_high",
            alert_type=AlertType.HIGH_ERROR_RATE,
            threshold=1.0,
            window_seconds=60,
            severity=AlertSeverity.WARNING,
            description="Error rate exceeds 1%",
        ),
        AlertRule(
            name="error_rate_critical",
            alert_type=AlertType.HIGH_ERROR_RATE,
            threshold=5.0,
            window_seconds=60,
            severity=AlertSeverity.CRITICAL,
            description="Error rate exceeds 5%",
        ),
    ]

    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self._alert_history: List[Alert] = []
        self._last_alert_time: Dict[str, datetime] = {}
        self._notification_channels: List[Callable[[Alert], None]] = []
        self._alert_counts: Dict[str, int] = defaultdict(int)

        for rule in self.DEFAULT_RULES:
            self.rules[rule.name] = rule

    def add_rule(self, rule: AlertRule) -> None:
        """Add or update an alert rule."""
        self.rules[rule.name] = rule
        logger.info(f"Alert rule added/updated: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info(f"Alert rule removed: {rule_name}")
            return True
        return False

    def add_notification_channel(self, channel: Callable[[Alert], None]) -> None:
        """Add a notification channel."""
        self._notification_channels.append(channel)

    def check_and_alert(
        self,
        metrics: dict,
        endpoint: Optional[str] = None,
    ) -> List[Alert]:
        """
        Check metrics against rules and generate alerts.

        Args:
            metrics: Metrics dictionary with stats
            endpoint: Optional endpoint being checked

        Returns:
            List of generated alerts
        """
        alerts = []

        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue

            if rule_name in self._last_alert_time:
                last = self._last_alert_time[rule_name]
                if datetime.utcnow() - last < timedelta(seconds=rule.cooldown_seconds):
                    continue

            alert = self._check_rule(rule, metrics, endpoint)
            if alert:
                alerts.append(alert)
                self._trigger_notifications(alert)
                self._last_alert_time[rule_name] = datetime.utcnow()
                self._alert_counts[rule_name] += 1
                self._alert_history.append(alert)

                if len(self._alert_history) > 1000:
                    self._alert_history = self._alert_history[-500:]

        return alerts

    def _check_rule(
        self,
        rule: AlertRule,
        metrics: dict,
        endpoint: Optional[str],
    ) -> Optional[Alert]:
        """Check a single rule against metrics."""
        value = None

        if rule.alert_type == AlertType.HIGH_LATENCY:
            value = metrics.get("p95_ms", 0)
        elif rule.alert_type == AlertType.HIGH_ERROR_RATE:
            value = metrics.get("error_rate", 0)
        elif rule.alert_type == AlertType.SLOW_ENDPOINT:
            value = metrics.get("avg_ms", 0)
        elif rule.alert_type == AlertType.BASELINE_DEVIATION:
            value = metrics.get("deviation_percent", 0)

        if value is None:
            return None

        if value > rule.threshold:
            return Alert(
                rule_name=rule.name,
                alert_type=rule.alert_type,
                severity=rule.severity,
                message=rule.description,
                value=value,
                threshold=rule.threshold,
                endpoint=endpoint,
            )

        return None

    def _trigger_notifications(self, alert: Alert) -> None:
        """Trigger all notification channels."""
        for channel in self._notification_channels:
            try:
                channel(alert)
            except Exception as e:
                logger.error(f"Notification channel error: {e}")

    def get_alert_history(
        self,
        limit: int = 100,
        severity: Optional[AlertSeverity] = None,
    ) -> List[dict]:
        """Get alert history."""
        alerts = self._alert_history[-limit:]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [a.to_dict() for a in alerts]

    def get_alert_stats(self) -> dict:
        """Get alert statistics."""
        return {
            "total_alerts": len(self._alert_history),
            "counts_by_rule": dict(self._alert_counts),
            "recent_alerts": len([a for a in self._alert_history if datetime.utcnow() - a.timestamp < timedelta(hours=1)]),
        }


alert_manager = AlertManager()


def log_notification(alert: Alert) -> None:
    """Default notification: log the alert."""
    level = {
        AlertSeverity.INFO: logging.INFO,
        AlertSeverity.WARNING: logging.WARNING,
        AlertSeverity.ERROR: logging.ERROR,
        AlertSeverity.CRITICAL: logging.CRITICAL,
    }.get(alert.severity, logging.WARNING)

    logger.log(
        level,
        f"[ALERT] {alert.rule_name}: {alert.message} "
        f"(value={alert.value:.2f}, threshold={alert.threshold:.2f}, endpoint={alert.endpoint})"
    )


alert_manager.add_notification_channel(log_notification)


class PerformanceMonitor:
    """
    Background performance monitor.

    Periodically checks performance metrics and triggers alerts.
    """

    def __init__(
        self,
        check_interval_seconds: int = 30,
        alert_manager: AlertManager = alert_manager,
    ):
        self.check_interval = check_interval_seconds
        self.alert_manager = alert_manager
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the monitor."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Performance monitor started")

    async def stop(self) -> None:
        """Stop the monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Performance monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_performance()
            except Exception as e:
                logger.error(f"Performance check error: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_performance(self) -> None:
        """Check performance and generate alerts."""
        from app.core.performance_middleware import metrics_collector

        stats = metrics_collector.get_stats()

        for endpoint, endpoint_stats in stats.items():
            if isinstance(endpoint_stats, dict) and "error" not in endpoint_stats:
                self.alert_manager.check_and_alert(endpoint_stats, endpoint)


performance_monitor = PerformanceMonitor()
