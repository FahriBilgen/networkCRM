"""Basic smoke test for the demo deployment.

Checks that the backend is reachable and the demo config is loaded
(via `/api/status`). Also verifies that the UI index is served at `/`
when a UI distribution is present. Run locally after `setup_demo`.
"""

import sys
import requests

BASE = "http://localhost:8000"
TIMEOUT = 3


def check_backend():
    try:
        r = requests.get(f"{BASE}/api/status", timeout=TIMEOUT)
        if r.status_code == 200:
            print("Backend reachable: /api/status OK")
            return True
        print("Backend status check failed with status:", r.status_code)
    except Exception as e:
        print("Backend not reachable:", e)
    return False


def check_ui_index():
    try:
        r = requests.get(f"{BASE}/", timeout=TIMEOUT)
        if r.status_code == 200 and "<!doctype html" in r.text.lower():
            print("UI index served at /: OK")
            return True
        print("UI index check returned status", r.status_code)
    except Exception as e:
        print("UI index not reachable:", e)
    return False


if __name__ == "__main__":
    ok = check_backend()
    ok_ui = check_ui_index()
    if ok and ok_ui:
        print("Smoke test passed")
        sys.exit(0)
    print("Smoke test failed")
    sys.exit(2)
