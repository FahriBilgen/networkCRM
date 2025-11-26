from __future__ import annotations

from fastapi.testclient import TestClient

from fortress_director import api
from fortress_director.llm.runtime_mode import set_llm_enabled

set_llm_enabled(False)


def test_run_turn_response_contains_demo_fields() -> None:
    client = TestClient(api.app)
    response = client.post("/api/run_turn", json={})
    assert response.status_code == 200
    payload = response.json()
    assert "turn_number" in payload
    assert "game_over" in payload
    assert "ending_id" in payload
