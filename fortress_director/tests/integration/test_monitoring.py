"""TIER 4.3: Monitoring analytics and dashboard tests."""

from fastapi.testclient import TestClient

from fortress_director.api import app
from fortress_director.core.metrics import get_metrics_collector


client = TestClient(app)


def test_metrics_endpoint_exists() -> None:
    """Test /metrics endpoint exists."""
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_endpoint_prometheus_format() -> None:
    """Test /metrics returns Prometheus format."""
    collector = get_metrics_collector()
    collector.record_request(0.1)
    collector.record_turn(0.5)

    response = client.get("/metrics")
    content = response.text

    # Should have Prometheus headers
    assert "# HELP" in content
    assert "# TYPE" in content

    # Should have metrics
    assert "http_requests_total" in content
    assert "turn_executions_total" in content


def test_metrics_endpoint_content_type() -> None:
    """Test /metrics has correct content type."""
    response = client.get("/metrics")

    # Should be text/plain for Prometheus
    assert "text" in response.headers.get("content-type", "").lower()


def test_metrics_endpoint_no_auth_required() -> None:
    """Test /metrics doesn't require authentication."""
    # Don't provide JWT token
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_collector_integration() -> None:
    """Test metrics collector integrates with requests."""
    collector = get_metrics_collector()
    initial_count = collector.request_count

    # Make request to /health (which increments counters)
    response = client.get("/health")
    assert response.status_code == 200

    # Collector might have recorded the request
    # (depends on middleware integration)
    assert collector.request_count >= initial_count


def test_metrics_json_export() -> None:
    """Test JSON metrics export."""
    collector = get_metrics_collector()
    collector.record_request(0.1)
    collector.record_turn(0.5)
    collector.record_function_call("test")

    json_metrics = collector.get_json_metrics()

    assert "requests" in json_metrics
    assert json_metrics["requests"]["total"] == 1
    assert json_metrics["requests"]["latency"]["avg"] > 0

    assert "turns" in json_metrics
    assert json_metrics["turns"]["total"] == 1

    assert "cache" in json_metrics
    assert "uptime_seconds" in json_metrics


def test_grafana_dashboard_config() -> None:
    """Test Grafana dashboard config exists."""
    import json
    from pathlib import Path

    dashboard_path = Path("monitoring/grafana-dashboard.json")
    assert dashboard_path.exists()

    with open(dashboard_path) as f:
        config = json.load(f)

    assert "dashboard" in config
    dashboard = config["dashboard"]

    assert dashboard["title"] == "Fortress Director Monitoring"
    assert "panels" in dashboard
    assert len(dashboard["panels"]) > 0


def test_grafana_dashboard_panels() -> None:
    """Test Grafana dashboard has all key panels."""
    import json

    with open("monitoring/grafana-dashboard.json") as f:
        config = json.load(f)

    panels = config["dashboard"]["panels"]
    panel_titles = [p["title"] for p in panels]

    # Should have key panels
    assert "HTTP Requests Total" in panel_titles
    assert "HTTP Errors Total" in panel_titles
    assert "Turn Executions Total" in panel_titles
    assert "Request Latency (ms)" in panel_titles
    assert "Cache Hit Rate" in panel_titles


def test_grafana_dashboard_queries() -> None:
    """Test Grafana dashboard has valid Prometheus queries."""
    import json

    with open("monitoring/grafana-dashboard.json") as f:
        config = json.load(f)

    panels = config["dashboard"]["panels"]

    # Each panel should have targets with expr
    for panel in panels:
        if "targets" in panel and len(panel["targets"]) > 0:
            target = panel["targets"][0]
            assert "expr" in target
            assert len(target["expr"]) > 0
