from fastapi.testclient import TestClient

from fortress_director import api
from fortress_director.llm.runtime_mode import set_llm_enabled

set_llm_enabled(False)


def test_run_turn_endpoint_returns_grid_payload() -> None:
    client = TestClient(api.app)
    response = client.post("/api/run_turn", json={"choice_id": "option_alpha"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["narrative"]
    assert payload["hud"]["turn"] >= 0
    assert len(payload["grid"]) >= 0
    assert "event_log" in payload
    assert len(payload["player_options"]) >= 0
    assert payload.get("trace_file")
    assert payload["session_id"]
    assert payload["theme_id"] == "siege_default"


def test_turn_trace_debug_endpoints() -> None:
    client = TestClient(api.app)
    post_resp = client.post("/api/run_turn", json={})
    assert post_resp.status_code == 200
    traces_resp = client.get("/api/dev/turn_traces")
    assert traces_resp.status_code == 200
    summaries = traces_resp.json()
    assert summaries
    turn_id = summaries[0]["turn"]
    trace_resp = client.get(f"/api/dev/turn_traces/{turn_id}")
    assert trace_resp.status_code == 200
    trace_payload = trace_resp.json()
    assert trace_payload["turn"] == turn_id
