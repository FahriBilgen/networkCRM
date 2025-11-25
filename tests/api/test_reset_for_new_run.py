from __future__ import annotations

from fastapi.testclient import TestClient

from fortress_director import api
from fortress_director.llm.runtime_mode import set_llm_enabled

set_llm_enabled(False)


def test_reset_for_new_run_returns_initial_session_payload() -> None:
    client = TestClient(api.app)
    response = client.post("/api/reset_for_new_run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"]
    assert isinstance(payload["hud"], dict)
    assert isinstance(payload["grid"], list)
    assert isinstance(payload["npc_positions"], dict)
    assert isinstance(payload["structures"], dict)
    assert isinstance(payload["event_markers"], list)
    assert "narrative" in payload
