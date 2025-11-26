"""TIER 4.2: Kubernetes deployment configuration tests."""

from pathlib import Path

import pytest
import yaml


def test_k8s_manifest_exists() -> None:
    """Test Kubernetes manifest file exists."""
    manifest_path = Path("k8s/fortress-director.yaml")
    assert manifest_path.exists(), "K8s manifest not found"


def test_k8s_manifest_valid_yaml() -> None:
    """Test Kubernetes manifest is valid YAML."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    # Should have multiple documents
    assert len(docs) > 0


def test_k8s_namespace_defined() -> None:
    """Test namespace is defined."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    namespaces = [d for d in docs if d.get("kind") == "Namespace"]
    assert len(namespaces) >= 1
    assert namespaces[0]["metadata"]["name"] == "fortress-director"


def test_k8s_config_map_defined() -> None:
    """Test ConfigMap for environment variables."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    configs = [d for d in docs if d.get("kind") == "ConfigMap"]
    assert len(configs) >= 1

    config = configs[0]
    assert "PYTHONUNBUFFERED" in config["data"]
    assert "LOG_LEVEL" in config["data"]


def test_k8s_pvc_defined() -> None:
    """Test PersistentVolumeClaims are defined."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    pvcs = [d for d in docs if d.get("kind") == "PersistentVolumeClaim"]
    assert len(pvcs) >= 2

    pvc_names = [pvc["metadata"]["name"] for pvc in pvcs]
    assert "fortress-data-pvc" in pvc_names
    assert "fortress-db-pvc" in pvc_names


def test_k8s_statefulset_defined() -> None:
    """Test StatefulSet is properly defined."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    statefulsets = [d for d in docs if d.get("kind") == "StatefulSet"]
    assert len(statefulsets) >= 1

    ss = statefulsets[0]
    assert ss["metadata"]["name"] == "fortress-director"
    assert ss["spec"]["serviceName"] == "fortress-director"


def test_k8s_statefulset_has_probes() -> None:
    """Test StatefulSet has health probes."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    ss = [d for d in docs if d.get("kind") == "StatefulSet"][0]
    container = ss["spec"]["template"]["spec"]["containers"][0]

    # Should have liveness and readiness probes
    assert "livenessProbe" in container
    assert "readinessProbe" in container

    # Probes should use /health endpoint
    assert container["livenessProbe"]["httpGet"]["path"] == "/health"
    assert container["readinessProbe"]["httpGet"]["path"] == "/health"


def test_k8s_service_defined() -> None:
    """Test Service is defined."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    services = [d for d in docs if d.get("kind") == "Service"]
    assert len(services) >= 1

    svc = services[0]
    assert svc["metadata"]["name"] == "fortress-director"
    assert svc["spec"]["type"] == "ClusterIP"


def test_k8s_hpa_defined() -> None:
    """Test HorizontalPodAutoscaler is defined."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    hpas = [d for d in docs if d.get("kind") == "HorizontalPodAutoscaler"]
    assert len(hpas) >= 1

    hpa = hpas[0]
    assert hpa["spec"]["minReplicas"] >= 1
    assert hpa["spec"]["maxReplicas"] >= hpa["spec"]["minReplicas"]


def test_k8s_hpa_has_metrics() -> None:
    """Test HPA has CPU and memory metrics."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    hpa = [d for d in docs if d.get("kind") == "HorizontalPodAutoscaler"][0]
    metrics = hpa["spec"]["metrics"]

    # Should have CPU and memory metrics
    metric_names = [m["resource"]["name"] for m in metrics]
    assert "cpu" in metric_names
    assert "memory" in metric_names


def test_k8s_network_policy_defined() -> None:
    """Test NetworkPolicy is defined."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    policies = [d for d in docs if d.get("kind") == "NetworkPolicy"]
    assert len(policies) >= 1

    policy = policies[0]
    assert policy["metadata"]["name"] == "fortress-director-netpol"


def test_k8s_statefulset_resources() -> None:
    """Test StatefulSet has resource requests and limits."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    ss = [d for d in docs if d.get("kind") == "StatefulSet"][0]
    container = ss["spec"]["template"]["spec"]["containers"][0]

    resources = container["resources"]
    assert "requests" in resources
    assert "limits" in resources

    # Requests should be less than limits
    req_mem = resources["requests"]["memory"]
    lim_mem = resources["limits"]["memory"]
    assert req_mem is not None
    assert lim_mem is not None


def test_k8s_volumes_mounted() -> None:
    """Test all required volumes are mounted."""
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    ss = [d for d in docs if d.get("kind") == "StatefulSet"][0]
    container = ss["spec"]["template"]["spec"]["containers"][0]

    volume_mounts = container.get("volumeMounts", [])
    mount_paths = [vm["mountPath"] for vm in volume_mounts]

    # Should mount app directories
    assert any("/app" in path for path in mount_paths)


@pytest.mark.integration
def test_k8s_deployment_complete() -> None:
    """Integration test: verify complete K8s deployment structure."""
    # Validate all components
    with open("k8s/fortress-director.yaml") as f:
        docs = list(yaml.safe_load_all(f))

    kinds = [d.get("kind") for d in docs if d]
    required_kinds = [
        "Namespace",
        "ConfigMap",
        "PersistentVolumeClaim",
        "StatefulSet",
        "Service",
        "HorizontalPodAutoscaler",
        "NetworkPolicy",
    ]

    for required in required_kinds:
        assert required in kinds, f"Missing {required} in K8s manifest"
