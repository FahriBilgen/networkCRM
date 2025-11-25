from __future__ import annotations

from fastapi.testclient import TestClient

from fortress_director import api
from fortress_director.llm.runtime_mode import set_llm_enabled

set_llm_enabled(False)


def test_turn_response_contains_visual_state_payload() -> None:
    client = TestClient(api.app)
    response = client.post("/api/run_turn", json={})
    payload = response.json()

    assert "npc_positions" in payload
    assert isinstance(payload["npc_positions"], dict)
    assert "structures" in payload
    assert isinstance(payload["structures"], dict)
    assert "event_markers" in payload
    assert isinstance(payload["event_markers"], list)
    assert "combat_summary" in payload
    assert "event_node" in payload
    assert payload["threat"]["phase"] == payload["threat_phase"]
