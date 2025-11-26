"""Prometheus metrics collection and export."""

from collections import defaultdict
from typing import Dict
import time


class MetricsCollector:
    """Collects and exports Prometheus-format metrics."""

    def __init__(self) -> None:
        """Initialize metrics collector."""
        self.request_count = 0
        self.turn_count = 0
        self.error_count = 0
        self.request_durations: list[float] = []
        self.turn_durations: list[float] = []
        self.function_calls: Dict[str, int] = defaultdict(int)
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = time.time()

    def record_request(self, duration: float) -> None:
        """Record HTTP request."""
        self.request_count += 1
        self.request_durations.append(duration)

    def record_turn(self, duration: float) -> None:
        """Record turn execution."""
        self.turn_count += 1
        self.turn_durations.append(duration)

    def record_error(self) -> None:
        """Record error occurrence."""
        self.error_count += 1

    def record_function_call(self, function_name: str) -> None:
        """Record function call."""
        self.function_calls[function_name] += 1

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        self.cache_misses += 1

    def get_request_latency_stats(self) -> Dict[str, float]:
        """Get request latency statistics."""
        if not self.request_durations:
            return {"min": 0, "max": 0, "avg": 0, "p95": 0, "p99": 0}

        durations = sorted(self.request_durations)
        return {
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
            "p95": durations[int(len(durations) * 0.95)],
            "p99": durations[int(len(durations) * 0.99)],
        }

    def get_turn_latency_stats(self) -> Dict[str, float]:
        """Get turn execution latency statistics."""
        if not self.turn_durations:
            return {"min": 0, "max": 0, "avg": 0, "p95": 0, "p99": 0}

        durations = sorted(self.turn_durations)
        return {
            "min": min(durations),
            "max": max(durations),
            "avg": sum(durations) / len(durations),
            "p95": durations[int(len(durations) * 0.95)],
            "p99": durations[int(len(durations) * 0.99)],
        }

    def get_cache_hit_rate(self) -> float:
        """Get cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Request metrics
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        lines.append(f"http_requests_total {self.request_count}")

        lines.append("# HELP http_errors_total Total HTTP errors")
        lines.append("# TYPE http_errors_total counter")
        lines.append(f"http_errors_total {self.error_count}")

        # Turn metrics
        lines.append("# HELP turn_executions_total Total turn executions")
        lines.append("# TYPE turn_executions_total counter")
        lines.append(f"turn_executions_total {self.turn_count}")

        # Latency metrics
        req_stats = self.get_request_latency_stats()
        lines.append("# HELP http_request_duration_seconds HTTP request duration")
        lines.append("# TYPE http_request_duration_seconds gauge")
        lines.append(
            f'http_request_duration_seconds{{quantile="0.5"}} ' f"{req_stats['avg']}"
        )
        lines.append(
            f'http_request_duration_seconds{{quantile="0.95"}} ' f"{req_stats['p95']}"
        )
        lines.append(
            f'http_request_duration_seconds{{quantile="0.99"}} ' f"{req_stats['p99']}"
        )

        turn_stats = self.get_turn_latency_stats()
        lines.append("# HELP turn_duration_seconds Turn execution duration")
        lines.append("# TYPE turn_duration_seconds gauge")
        lines.append(f'turn_duration_seconds{{quantile="0.5"}} ' f"{turn_stats['avg']}")
        lines.append(
            f'turn_duration_seconds{{quantile="0.95"}} ' f"{turn_stats['p95']}"
        )
        lines.append(
            f'turn_duration_seconds{{quantile="0.99"}} ' f"{turn_stats['p99']}"
        )

        # Cache metrics
        lines.append("# HELP cache_hits_total Total cache hits")
        lines.append("# TYPE cache_hits_total counter")
        lines.append(f"cache_hits_total {self.cache_hits}")

        lines.append("# HELP cache_misses_total Total cache misses")
        lines.append("# TYPE cache_misses_total counter")
        lines.append(f"cache_misses_total {self.cache_misses}")

        lines.append("# HELP cache_hit_rate Cache hit rate")
        lines.append("# TYPE cache_hit_rate gauge")
        lines.append(f"cache_hit_rate {self.get_cache_hit_rate()}")

        # Function call metrics
        for func_name, count in self.function_calls.items():
            lines.append(f'function_calls_total{{function="{func_name}"}} {count}')

        # Uptime
        uptime = time.time() - self.start_time
        lines.append("# HELP process_uptime_seconds Process uptime")
        lines.append("# TYPE process_uptime_seconds gauge")
        lines.append(f"process_uptime_seconds {uptime}")

        return "\n".join(lines)

    def get_json_metrics(self) -> Dict:
        """Get metrics as JSON for API responses."""
        return {
            "requests": {
                "total": self.request_count,
                "errors": self.error_count,
                "latency": self.get_request_latency_stats(),
            },
            "turns": {
                "total": self.turn_count,
                "latency": self.get_turn_latency_stats(),
            },
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": self.get_cache_hit_rate(),
            },
            "functions": dict(self.function_calls),
            "uptime_seconds": time.time() - self.start_time,
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.request_count = 0
        self.turn_count = 0
        self.error_count = 0
        self.request_durations.clear()
        self.turn_durations.clear()
        self.function_calls.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.start_time = time.time()


# Global metrics instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
