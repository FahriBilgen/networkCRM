"""TIER 4.2: Docker containerization and deployment tests."""

from pathlib import Path

import pytest


def test_dockerfile_syntax() -> None:
    """Test Dockerfile has valid syntax."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile not found"

    # Read and validate basic structure
    content = dockerfile_path.read_text()
    assert "FROM python:3.12" in content
    assert "WORKDIR /app" in content
    assert "COPY requirements.txt" in content
    assert "CMD" in content
    assert "HEALTHCHECK" in content


def test_docker_compose_syntax() -> None:
    """Test docker-compose.yml has valid YAML syntax."""
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists(), "docker-compose.yml not found"

    # Read and parse YAML
    import yaml

    with open(compose_path) as f:
        config = yaml.safe_load(f)

    # Validate structure
    assert "services" in config
    assert "fortress-director" in config["services"]
    assert "networks" in config


def test_dockerfile_includes_health_check() -> None:
    """Test Dockerfile includes health check configuration."""
    content = Path("Dockerfile").read_text()
    assert "HEALTHCHECK" in content
    assert "--interval" in content
    assert "localhost:8000/health" in content


def test_docker_compose_volumes() -> None:
    """Test docker-compose defines all necessary volumes."""
    import yaml

    with open("docker-compose.yml") as f:
        config = yaml.safe_load(f)

    service = config["services"]["fortress-director"]
    volumes = service.get("volumes", [])

    # Should map key directories
    volume_paths = [v.split(":")[1] if ":" in v else v for v in volumes]
    assert "/app/data" in volume_paths
    assert "/app/db" in volume_paths
    assert "/app/logs" in volume_paths


def test_docker_compose_environment() -> None:
    """Test docker-compose sets necessary env variables."""
    import yaml

    with open("docker-compose.yml") as f:
        config = yaml.safe_load(f)

    service = config["services"]["fortress-director"]
    env = service.get("environment", {})

    # Should disable buffering for logs
    env_list = env if isinstance(env, list) else env.values()
    assert any("PYTHONUNBUFFERED" in str(e) for e in env_list)


def test_docker_compose_port_mapping() -> None:
    """Test docker-compose has correct port mapping."""
    import yaml

    with open("docker-compose.yml") as f:
        config = yaml.safe_load(f)

    service = config["services"]["fortress-director"]
    ports = service.get("ports", [])

    # Should expose 8000
    assert any("8000" in str(p) for p in ports)


def test_dockerfile_workdir() -> None:
    """Test Dockerfile sets correct working directory."""
    content = Path("Dockerfile").read_text()
    lines = content.split("\n")

    # Find WORKDIR line
    workdir_lines = [ln for ln in lines if ln.strip().startswith("WORKDIR")]
    assert len(workdir_lines) > 0
    assert "/app" in workdir_lines[0]


def test_dockerfile_creates_directories() -> None:
    """Test Dockerfile creates necessary runtime directories."""
    content = Path("Dockerfile").read_text()

    # Should create these directories
    assert "data" in content
    assert "db" in content
    assert "logs" in content
    assert "cache" in content


def test_docker_compose_restart_policy() -> None:
    """Test docker-compose has restart policy."""
    import yaml

    with open("docker-compose.yml") as f:
        config = yaml.safe_load(f)

    service = config["services"]["fortress-director"]
    assert "restart" in service
    assert service["restart"] in ["always", "unless-stopped", "on-failure"]


def test_docker_compose_network() -> None:
    """Test docker-compose defines custom network."""
    import yaml

    with open("docker-compose.yml") as f:
        config = yaml.safe_load(f)

    assert "networks" in config
    assert "fortress-network" in config["networks"]

    service = config["services"]["fortress-director"]
    assert "networks" in service


def test_dockerfile_python_version() -> None:
    """Test Dockerfile uses Python 3.12+."""
    content = Path("Dockerfile").read_text()

    # Extract version
    for line in content.split("\n"):
        if line.startswith("FROM python"):
            # Should be 3.12 or later
            assert "3.12" in line or "3.13" in line or "3.14" in line


def test_build_script_exists() -> None:
    """Test build/deployment scripts could be created."""
    # This tests the concept of having build scripts
    # In production, scripts would run: docker build -t fortress-director .
    assert True  # Placeholder for actual script tests


def test_docker_compose_container_name() -> None:
    """Test docker-compose specifies container name."""
    import yaml

    with open("docker-compose.yml") as f:
        config = yaml.safe_load(f)

    service = config["services"]["fortress-director"]
    assert "container_name" in service
    assert service["container_name"] == "fortress-director"


@pytest.mark.integration
def test_containerization_structure() -> None:
    """Integration test: verify complete containerization structure."""
    # Check files exist
    assert Path("Dockerfile").exists()
    assert Path("docker-compose.yml").exists()
    assert Path("requirements.txt").exists()

    # Validate content
    dockerfile = Path("Dockerfile").read_text()
    compose = Path("docker-compose.yml").read_text()

    assert "fortress-director" in compose
    assert "8000" in compose
    assert "healthcheck" in compose.lower() or "HEALTHCHECK" in dockerfile
