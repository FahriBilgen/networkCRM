"""TIER 4.3: Monitoring and metrics tests."""

from fortress_director.core.metrics import (
    MetricsCollector,
    get_metrics_collector,
)


def test_metrics_collector_creation() -> None:
    """Test MetricsCollector can be instantiated."""
    collector = MetricsCollector()
    assert collector is not None
    assert collector.request_count == 0
    assert collector.turn_count == 0


def test_record_request() -> None:
    """Test recording HTTP requests."""
    collector = MetricsCollector()
    collector.record_request(0.1)
    collector.record_request(0.2)
    collector.record_request(0.15)

    assert collector.request_count == 3
    assert len(collector.request_durations) == 3


def test_record_turn() -> None:
    """Test recording turn executions."""
    collector = MetricsCollector()
    collector.record_turn(0.5)
    collector.record_turn(0.6)

    assert collector.turn_count == 2
    assert len(collector.turn_durations) == 2


def test_record_error() -> None:
    """Test recording errors."""
    collector = MetricsCollector()
    collector.record_error()
    collector.record_error()
    collector.record_error()

    assert collector.error_count == 3


def test_record_function_call() -> None:
    """Test recording function calls."""
    collector = MetricsCollector()
    collector.record_function_call("move_npc")
    collector.record_function_call("move_npc")
    collector.record_function_call("spawn_item")

    assert collector.function_calls["move_npc"] == 2
    assert collector.function_calls["spawn_item"] == 1


def test_cache_metrics() -> None:
    """Test cache hit/miss recording."""
    collector = MetricsCollector()
    collector.record_cache_hit()
    collector.record_cache_hit()
    collector.record_cache_miss()

    assert collector.cache_hits == 2
    assert collector.cache_misses == 1
    assert collector.get_cache_hit_rate() == pytest.approx(2 / 3, rel=0.01)


def test_request_latency_stats() -> None:
    """Test request latency statistics."""
    collector = MetricsCollector()
    durations = [0.1, 0.2, 0.15, 0.3, 0.05]

    for d in durations:
        collector.record_request(d)

    stats = collector.get_request_latency_stats()
    assert stats["min"] == 0.05
    assert stats["max"] == 0.3
    assert 0.15 < stats["avg"] < 0.17
    assert stats["p95"] >= stats["avg"]
    assert stats["p99"] >= stats["avg"]


def test_turn_latency_stats() -> None:
    """Test turn execution latency statistics."""
    collector = MetricsCollector()
    durations = [0.5, 0.6, 0.55, 0.7, 0.45]

    for d in durations:
        collector.record_turn(d)

    stats = collector.get_turn_latency_stats()
    assert stats["min"] == 0.45
    assert stats["max"] == 0.7
    assert 0.55 < stats["avg"] < 0.60
    assert stats["p95"] >= stats["avg"]


def test_cache_hit_rate_empty() -> None:
    """Test cache hit rate with no data."""
    collector = MetricsCollector()
    assert collector.get_cache_hit_rate() == 0.0


def test_prometheus_format_export() -> None:
    """Test Prometheus format metrics export."""
    collector = MetricsCollector()
    collector.record_request(0.1)
    collector.record_turn(0.5)
    collector.record_error()
    collector.record_cache_hit()

    prometheus_output = collector.export_prometheus()

    assert "http_requests_total" in prometheus_output
    assert "turn_executions_total" in prometheus_output
    assert "http_errors_total" in prometheus_output
    assert "cache_hits_total" in prometheus_output
    assert "process_uptime_seconds" in prometheus_output


def test_json_metrics_export() -> None:
    """Test JSON format metrics export."""
    collector = MetricsCollector()
    collector.record_request(0.1)
    collector.record_turn(0.5)
    collector.record_function_call("test_func")

    json_metrics = collector.get_json_metrics()

    assert "requests" in json_metrics
    assert "turns" in json_metrics
    assert "cache" in json_metrics
    assert "functions" in json_metrics
    assert "uptime_seconds" in json_metrics

    assert json_metrics["requests"]["total"] == 1
    assert json_metrics["turns"]["total"] == 1
    assert "test_func" in json_metrics["functions"]


def test_metrics_reset() -> None:
    """Test resetting metrics."""
    collector = MetricsCollector()
    collector.record_request(0.1)
    collector.record_turn(0.5)
    collector.record_error()

    assert collector.request_count > 0
    assert collector.turn_count > 0
    assert collector.error_count > 0

    collector.reset()

    assert collector.request_count == 0
    assert collector.turn_count == 0
    assert collector.error_count == 0
    assert collector.cache_hits == 0
    assert collector.cache_misses == 0


def test_global_metrics_instance() -> None:
    """Test global metrics instance is singleton."""
    collector1 = get_metrics_collector()
    collector2 = get_metrics_collector()

    assert collector1 is collector2

    # Record on first, check on second
    collector1.record_request(0.1)
    assert collector2.request_count == 1


def test_multiple_collectors_independent() -> None:
    """Test multiple collector instances are independent."""
    collector1 = MetricsCollector()
    collector2 = MetricsCollector()

    collector1.record_request(0.1)
    collector2.record_request(0.2)

    assert collector1.request_count == 1
    assert collector2.request_count == 1


def test_latency_percentiles() -> None:
    """Test percentile calculations."""
    collector = MetricsCollector()

    # Create 100 samples
    for i in range(100):
        collector.record_request(i * 0.01)  # 0 to 0.99

    stats = collector.get_request_latency_stats()

    # P95 should be around 95th percentile
    assert 0.90 < stats["p95"] < 1.0
    assert 0.95 < stats["p99"] < 1.0


# Import pytest after all tests for lazy evaluation
import pytest  # noqa: E402, F401
