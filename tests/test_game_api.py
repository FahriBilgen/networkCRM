import os
import pytest
from fastapi.testclient import TestClient


os.environ["FORTRESS_OFFLINE"] = "1"

from fortress_director.api import app  # noqa: E402


client = TestClient(app)


def test_game_reset_and_state_and_options_and_turn():
    # Reset
    r = client.post("/game/reset")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["api_version"] == "v1"

    # State
    r = client.get("/game/state")
    assert r.status_code == 200
    st = r.json()
    assert st["api_version"] == "v1"
    assert "turn" in st and "time" in st

    # Options (peek)
    r = client.get("/game/options")
    assert r.status_code == 200
    data = r.json()
    assert data["api_version"] == "v1"
    assert "options" in data
    assert isinstance(data["options"], list)

    # Play a turn default (no choice)
    r = client.post("/game/turn", json={"choice_id": None})
    assert r.status_code == 200
    result = r.json()
    assert result["api_version"] == "v1"
    assert isinstance(result, dict)
    assert "win_loss" in result


def test_contract_schema_endpoints():
    r = client.get("/api/schema/v1")
    assert r.status_code == 200
    body = r.json()
    assert body["api_version"] == "v1"
    assert body["contract_version"] == "v1"
    assert "player_view" in body["components"]
    assert "options" in body["components"]
    assert "safe_function_results" in body["components"]

    schema_resp = client.get("/api/schema/v1/player_view")
    assert schema_resp.status_code == 200
    schema_body = schema_resp.json()
    assert schema_body["component"] == "player_view"
    schema = schema_body["schema"]
    assert schema["title"] == "PlayerView"
    assert "$schema" in schema

    options_schema = client.get("/api/schema/v1/options")
    assert options_schema.status_code == 200
    assert options_schema.json()["schema"]["type"] == "array"


def test_contract_schema_invalid_version():
    r = client.get("/api/schema/v2")
    assert r.status_code == 404
