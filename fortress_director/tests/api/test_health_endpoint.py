"""Health endpoint API tests."""

from fortress_director.api import app


def test_health_endpoint_returns_200() -> None:
    """Test /health endpoint returns 200 OK."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_health_endpoint_structure() -> None:
    """Test /health endpoint returns required fields."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "uptime_seconds" in data
    assert "timestamp" in data
    assert "checks" in data
    assert "errors" in data


def test_health_endpoint_status_values() -> None:
    """Test /health status field has valid values."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/health")
    data = response.json()

    assert data["status"] in ["ok", "degraded", "error"]
    assert isinstance(data["uptime_seconds"], (int, float))
    assert data["uptime_seconds"] >= 0
    assert isinstance(data["checks"], dict)
    assert isinstance(data["errors"], list)


def test_health_endpoint_version() -> None:
    """Test /health returns version."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/health")
    data = response.json()

    assert data["version"] == "0.3.0"


def test_health_checks_content() -> None:
    """Test /health checks contain expected data."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/health")
    data = response.json()
    checks = data["checks"]

    assert "python_version" in checks
    assert "themes" in checks
    assert "safe_functions" in checks
    assert checks["safe_functions"]["count"] >= 75


def test_health_endpoint_no_auth_required() -> None:
    """Test /health endpoint doesn't require authentication."""
    from fastapi.testclient import TestClient

    client = TestClient(app)
    # Should work without any headers
    response = client.get("/health")
    assert response.status_code == 200
