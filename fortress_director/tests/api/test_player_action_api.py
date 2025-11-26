from fastapi.testclient import TestClient

from fortress_director import api
from fortress_director.llm.runtime_mode import set_llm_enabled

set_llm_enabled(False)


def test_select_action_and_run_turn_clears_context():
    # Select an action
    payload = api.SelectActionRequest(
        session_id=None,
        action_id="repair_wall",
        params={"structure_id": "western_wall", "amount": 2},
    )
    resp = api.select_player_action(payload)
    assert resp.session_id
    session_id = resp.session_id

    # Ensure session has queued context
    sid, ctx, _ = api._SESSION_MANAGER.get_or_create(session_id)
    assert ctx.player_action_context is not None

    # Run a turn and ensure it consumes the context and clears it
    run_payload = api.RunTurnRequest(session_id=session_id)
    run_resp = api.run_turn_endpoint(run_payload)
    # returned response contains original context
    assert run_resp.player_action_context is not None
    # but session should be cleared after run
    sid2, ctx2, _ = api._SESSION_MANAGER.get_or_create(session_id)
    assert ctx2.player_action_context is None


def test_select_action_validates_parameters() -> None:
    client = TestClient(api.app)
    response = client.post(
        "/api/select_action",
        json={"action_id": "move_npc", "params": {"npc_id": "ghost", "x": 1, "y": 2}},
    )
    assert response.status_code == 400
    assert "npc not found" in response.json()["detail"]


def test_select_action_and_run_turn_flow() -> None:
    client = TestClient(api.app)
    select_resp = client.post(
        "/api/select_action",
        json={
            "action_id": "move_npc",
            "params": {"npc_id": "scout_rhea", "x": 2, "y": 3},
        },
    )
    assert select_resp.status_code == 200
    payload = select_resp.json()
    session_id = payload["session_id"]
    assert payload["player_action_context"]["required_calls"]
    run_resp = client.post("/api/run_turn", json={"session_id": session_id})
    assert run_resp.status_code == 200
    executed = [entry["function"] for entry in run_resp.json()["executed_actions"]]
    assert "move_npc" in executed
