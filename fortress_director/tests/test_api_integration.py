import pytest
from fastapi.testclient import TestClient
from fortress_director.api import app

client = TestClient(app)


def test_api_update_motif():
    response = client.post("/motif/update", json={"new_motif": "api_motif"})
    assert response.status_code == 200
    assert response.json()["motif"] == "api_motif"


def test_api_update_character():
    payload = {"name": "ApiChar", "summary": "api summary"}
    response = client.post("/character/update", json=payload)
    assert response.status_code == 200
    assert response.json()["character"] == "ApiChar"


def test_api_update_prompt():
    payload = {
        "agent": "character",
        "new_prompt": "api prompt",
        "persist_to_file": False,
    }
    response = client.post("/prompt/update", json=payload)
    assert response.status_code == 200
    assert response.json()["agent"] == "character"


def test_api_mutate_safe_function_remove():
    payload = {"name": "dummy_func", "remove": True}
    response = client.post("/safe_function/mutate", json=payload)
    assert response.status_code == 200
    assert response.json()["removed"] is True
