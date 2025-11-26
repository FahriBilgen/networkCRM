"""TIER 4.1: API endpoint stress tests."""

import time
import threading
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from fortress_director.api import app


client = TestClient(app)


def test_concurrent_auth_requests() -> None:
    """Test /auth/login handles concurrent requests."""
    results = []
    lock = threading.Lock()

    def login_request(attempt: int) -> dict:
        response = client.post(
            "/auth/login",
            json={
                "username": f"user_{attempt}",
                "password": "test_password",
            },
        )
        with lock:
            results.append(response.status_code)
        return response.json()

    # 10 concurrent logins
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(login_request, i) for i in range(10)]
        _ = [f.result() for f in futures]

    # All should get responses (200 OK or 401 Unauthorized)
    assert len(results) == 10
    assert all(code in [200, 401] for code in results)


def test_health_endpoint_under_load() -> None:
    """Test /health endpoint is fast and stable under load."""
    response_times = []
    lock = threading.Lock()

    def health_check() -> None:
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        with lock:
            response_times.append(elapsed)

        assert response.status_code == 200
        assert "status" in response.json()

    # 50 concurrent health checks
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(health_check) for _ in range(50)]
        _ = [f.result() for f in futures]

    # All should complete
    assert len(response_times) == 50

    # Average should be fast
    avg_time = sum(response_times) / len(response_times)
    assert avg_time < 1.0  # < 1 second average


def test_mixed_endpoint_load() -> None:
    """Test API handles mixed endpoint types under load."""
    results = []
    lock = threading.Lock()

    def mixed_request(req_id: int) -> tuple:
        try:
            if req_id % 3 == 0:
                # Test /health
                resp = client.get("/health")
                endpoint = "health"
            elif req_id % 3 == 1:
                # Test /auth/login
                resp = client.post(
                    "/auth/login",
                    json={
                        "username": f"user_{req_id}",
                        "password": "pass",
                    },
                )
                endpoint = "auth"
            else:
                # Test /health again
                resp = client.get("/health")
                endpoint = "health"

            with lock:
                results.append((endpoint, resp.status_code, True))

            return (endpoint, resp.status_code)
        except Exception as e:
            with lock:
                results.append(("error", None, False))
            raise

    # 30 mixed requests
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(mixed_request, i) for i in range(30)]
        try:
            _ = [f.result() for f in futures]
        except Exception:
            pass

    # Most should succeed
    successful = sum(1 for _, _, success in results if success)
    assert successful >= 25


def test_rapid_sequential_requests() -> None:
    """Test API handles rapid-fire sequential requests."""
    results = []

    def rapid_requests() -> int:
        success_count = 0
        for i in range(20):
            response = client.get("/health")
            if response.status_code == 200:
                success_count += 1
        return success_count

    # 5 threads doing rapid requests
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(rapid_requests) for _ in range(5)]
        results = [f.result() for f in futures]

    # All should mostly succeed
    assert sum(results) >= 90  # At least 90 out of 100


def test_endpoint_consistency_under_concurrent_load() -> None:
    """Test responses are consistent across concurrent requests."""
    health_responses = []
    lock = threading.Lock()

    def check_health_consistency() -> dict:
        response = client.get("/health")
        data = response.json()

        with lock:
            health_responses.append(data)

        # Verify structure
        assert "status" in data
        assert "version" in data
        assert response.status_code == 200

        return data

    # 20 concurrent health checks
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_health_consistency) for _ in range(20)]
        _ = [f.result() for f in futures]

    # All should have same structure
    assert len(health_responses) == 20

    # All should have same status
    statuses = set(r.get("status") for r in health_responses)
    assert len(statuses) <= 2  # healthy or degraded


def test_error_handling_under_load() -> None:
    """Test API handles errors gracefully under load."""
    errors = []
    successes = 0
    lock = threading.Lock()

    def test_error_scenario(scenario_id: int) -> bool:
        nonlocal successes
        try:
            if scenario_id % 5 == 0:
                # Invalid endpoint
                response = client.get("/invalid_endpoint_xyz")
                status = response.status_code
            else:
                # Valid endpoint
                response = client.get("/health")
                status = response.status_code

            if 200 <= status < 400:
                with lock:
                    successes += 1
            else:
                with lock:
                    errors.append(status)

            return True
        except Exception:
            with lock:
                errors.append(str(type(Exception).__name__))
            return False

    # 25 mixed scenarios
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(test_error_scenario, i) for i in range(25)]
        results = [f.result() for f in futures]

    # All should complete
    assert len(results) == 25
    # Successes should dominate
    assert successes >= 15


def test_response_time_stability() -> None:
    """Test response times remain stable across many requests."""
    times_by_endpoint = {"health": [], "auth": []}
    lock = threading.Lock()

    def timed_request(req_id: int) -> None:
        start = time.time()

        if req_id % 2 == 0:
            client.get("/health")
            endpoint = "health"
        else:
            client.post(
                "/auth/login",
                json={"username": f"user_{req_id}", "password": "pass"},
            )
            endpoint = "auth"

        elapsed = time.time() - start

        with lock:
            times_by_endpoint[endpoint].append(elapsed)

    # 40 requests split between endpoints
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(timed_request, i) for i in range(40)]
        _ = [f.result() for f in futures]

    # Both endpoints should have data
    assert len(times_by_endpoint["health"]) >= 15
    assert len(times_by_endpoint["auth"]) >= 15

    # Response times should be reasonable
    health_avg = sum(times_by_endpoint["health"]) / len(times_by_endpoint["health"])
    assert health_avg < 2.0
