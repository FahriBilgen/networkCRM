from fastapi.testclient import TestClient

from fortress_director import api
from fortress_director.llm.runtime_mode import set_llm_enabled

set_llm_enabled(False)


def test_session_id_preserves_state_across_turns() -> None:
    client = TestClient(api.app)
    first = client.post("/api/run_turn", json={})
    assert first.status_code == 200
    payload_one = first.json()
    session_id = payload_one["session_id"]
    turn_one = payload_one["hud"]["turn"]

    second = client.post("/api/run_turn", json={"session_id": session_id})
    assert second.status_code == 200
    payload_two = second.json()
    assert payload_two["session_id"] == session_id
    assert payload_two["hud"]["turn"] == turn_one + 1


def test_sessions_do_not_leak_across_ids() -> None:
    client = TestClient(api.app)
    base_a = client.post("/api/run_turn", json={}).json()
    session_a = base_a["session_id"]
    turn_a = base_a["hud"]["turn"]

    base_b = client.post("/api/run_turn", json={}).json()
    session_b = base_b["session_id"]
    turn_b = base_b["hud"]["turn"]
    assert session_a != session_b

    follow_a = client.post("/api/run_turn", json={"session_id": session_a}).json()
    follow_b = client.post("/api/run_turn", json={"session_id": session_b}).json()

    assert follow_a["hud"]["turn"] == turn_a + 1
    assert follow_b["hud"]["turn"] == turn_b + 1
