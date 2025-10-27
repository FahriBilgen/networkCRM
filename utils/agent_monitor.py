"""Agent performance monitoring utilities."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from settings import SETTINGS

LOGGER = logging.getLogger(__name__)


@dataclass
class AgentPerformanceMetrics:
    """Performance metrics for an agent."""

    agent_name: str
    response_times: List[float] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    consistency_violations: int = 0
    quality_issues: int = 0
    last_response_time: Optional[float] = None

    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 100.0
        return (self.success_count / total) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_name": self.agent_name,
            "response_times": self.response_times,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "consistency_violations": self.consistency_violations,
            "quality_issues": self.quality_issues,
            "average_response_time": self.average_response_time,
            "success_rate": self.success_rate,
            "last_response_time": self.last_response_time,
        }


class AgentMonitor:
    """Monitor agent performance and consistency."""

    def __init__(self):
        self.metrics: Dict[str, AgentPerformanceMetrics] = {}
        self.monitoring_enabled = True

    def get_metrics(self, agent_name: str) -> AgentPerformanceMetrics:
        """Get or create metrics for an agent."""
        if agent_name not in self.metrics:
            self.metrics[agent_name] = AgentPerformanceMetrics(agent_name=agent_name)
        return self.metrics[agent_name]

    def record_response_time(self, agent_name: str, response_time: float) -> None:
        """Record response time for an agent."""
        if not self.monitoring_enabled:
            return

        metrics = self.get_metrics(agent_name)
        metrics.response_times.append(response_time)
        metrics.last_response_time = response_time

        # Keep only last 100 response times
        if len(metrics.response_times) > 100:
            metrics.response_times = metrics.response_times[-100:]

    def record_success(self, agent_name: str) -> None:
        """Record successful agent execution."""
        if not self.monitoring_enabled:
            return

        metrics = self.get_metrics(agent_name)
        metrics.success_count += 1

    def record_failure(self, agent_name: str, error_type: str = "unknown") -> None:
        """Record failed agent execution."""
        if not self.monitoring_enabled:
            return

        metrics = self.get_metrics(agent_name)
        metrics.failure_count += 1

        if error_type == "consistency_violation":
            metrics.consistency_violations += 1
        elif error_type == "quality_issue":
            metrics.quality_issues += 1

    def detect_performance_issues(self, agent_name: str) -> List[str]:
        """Detect potential performance issues for an agent."""
        metrics = self.get_metrics(agent_name)
        issues = []

        # Check response time
        if metrics.average_response_time > 30.0:
            issues.append(".1f")

        # Check success rate
        if metrics.success_rate < 80.0:
            issues.append(".1f")

        # Check consistency violations
        if metrics.consistency_violations > 5:
            issues.append(
                f"High consistency violations: {metrics.consistency_violations}"
            )

        # Check quality issues
        if metrics.quality_issues > 3:
            issues.append(f"High quality issues: {metrics.quality_issues}")

        return issues

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {"timestamp": time.time(), "agents": {}, "system_health": "good"}

        total_issues = 0
        for agent_name, metrics in self.metrics.items():
            report["agents"][agent_name] = metrics.to_dict()
            issues = self.detect_performance_issues(agent_name)
            if issues:
                report["agents"][agent_name]["issues"] = issues
                total_issues += len(issues)

        # Determine system health
        if total_issues > 5:
            report["system_health"] = "critical"
        elif total_issues > 2:
            report["system_health"] = "warning"
        else:
            report["system_health"] = "good"

        return report

    def save_report(self, filepath: Optional[Path] = None) -> None:
        """Save performance report to file."""
        if filepath is None:
            filepath = SETTINGS.cache_dir / "agent_performance_report.json"

        report = self.get_performance_report()

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            LOGGER.info(f"Performance report saved to {filepath}")
        except Exception as e:
            LOGGER.error(f"Failed to save performance report: {e}")

    def log_performance_summary(self) -> None:
        """Log a summary of current performance metrics."""
        if not self.monitoring_enabled:
            return

        LOGGER.info("=== Agent Performance Summary ===")

        for agent_name, metrics in self.metrics.items():
            LOGGER.info(f"{agent_name}:")
            LOGGER.info(f"  Response time: {metrics.average_response_time:.2f}s")
            LOGGER.info(f"  Success rate: {metrics.success_rate:.1f}%")
            LOGGER.info(f"  Consistency violations: {metrics.consistency_violations}")
            LOGGER.info(f"  Quality issues: {metrics.quality_issues}")

            issues = self.detect_performance_issues(agent_name)
            if issues:
                LOGGER.warning(f"  Issues: {issues}")

        report = self.get_performance_report()
        LOGGER.info(f"System health: {report['system_health']}")


# Global monitor instance
AGENT_MONITOR = AgentMonitor()
