"""Health check endpoint tests."""

from fortress_director.core.health_check import (
    EnvironmentValidator,
    HealthStatus,
    get_health_status,
)


def test_environment_validator_basic() -> None:
    """Test environment validation passes basic checks."""
    success, errors = EnvironmentValidator.validate()
    assert success or len(errors) > 0
    assert isinstance(errors, list)


def test_environment_validator_get_checks() -> None:
    """Test environment checks are gathered correctly."""
    checks = EnvironmentValidator.get_checks()
    assert "python_version" in checks
    assert "data_dir" in checks
    assert "db_dir" in checks
    assert "logs_dir" in checks
    assert "database" in checks
    assert "themes" in checks
    assert "safe_functions" in checks


def test_python_version_check() -> None:
    """Verify Python version is correctly reported."""
    checks = EnvironmentValidator.get_checks()
    py_version = checks["python_version"]
    assert isinstance(py_version, str)
    parts = py_version.split(".")
    assert len(parts) == 3
    for part in parts:
        assert part.isdigit()


def test_directory_checks() -> None:
    """Verify directory existence checks."""
    checks = EnvironmentValidator.get_checks()
    for dir_name in ["data_dir", "db_dir", "logs_dir"]:
        assert "exists" in checks[dir_name]
        assert "writable" in checks[dir_name]
        assert isinstance(checks[dir_name]["exists"], bool)
        assert isinstance(checks[dir_name]["writable"], bool)


def test_database_checks() -> None:
    """Verify database checks."""
    checks = EnvironmentValidator.get_checks()
    assert "database" in checks
    assert "connected" in checks["database"]


def test_themes_checks() -> None:
    """Verify themes are loaded."""
    checks = EnvironmentValidator.get_checks()
    assert "themes" in checks
    assert "count" in checks["themes"]
    assert checks["themes"]["count"] > 0
    assert "default_available" in checks["themes"]
    assert checks["themes"]["default_available"] is True


def test_safe_functions_checks() -> None:
    """Verify safe functions are loaded."""
    checks = EnvironmentValidator.get_checks()
    assert "safe_functions" in checks
    assert "count" in checks["safe_functions"]
    assert checks["safe_functions"]["count"] >= 75
    assert "categories" in checks["safe_functions"]


def test_health_status_structure() -> None:
    """Test health status has correct structure."""
    status = get_health_status()
    assert isinstance(status, HealthStatus)
    assert status.status in ["ok", "degraded", "error"]
    assert status.version == "0.3.0"
    assert status.uptime_seconds >= 0
    assert status.timestamp
    assert isinstance(status.checks, dict)
    assert isinstance(status.errors, list)


def test_health_status_uptime() -> None:
    """Verify uptime is reported correctly."""
    status1 = get_health_status()
    import time

    time.sleep(0.01)
    status2 = get_health_status()

    # Second call should have slightly higher uptime
    assert status2.uptime_seconds >= status1.uptime_seconds


def test_health_status_timestamp() -> None:
    """Verify timestamp is ISO format."""
    status = get_health_status()
    # Should be ISO format: 2025-11-26T...
    assert "T" in status.timestamp
    assert "Z" in status.timestamp or "+" in status.timestamp


def test_health_checks_completeness() -> None:
    """Verify all important checks are present."""
    status = get_health_status()
    checks = status.checks

    # Must have core checks
    assert "python_version" in checks
    assert "themes" in checks
    assert "safe_functions" in checks

    # Directory checks
    assert "data_dir" in checks
    assert "db_dir" in checks
    assert "logs_dir" in checks

    # Database check
    assert "database" in checks
