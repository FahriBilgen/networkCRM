import json
from unittest.mock import MagicMock

import pytest

from fortress_director.agents import DirectorAgent
from fortress_director.llm.ollama_client import OllamaClientError
from fortress_director.llm.runtime_mode import set_llm_enabled


@pytest.fixture(autouse=True)
def enable_llm_for_tests():
    """Ensure LLM mode is enabled for all tests in this module."""
    set_llm_enabled(True)
    yield
    set_llm_enabled(True)


def _sample_state() -> dict:
    return {
        "turn": 4,
        "world": {"stability": 62, "resources": 80, "threat_level": "volatile"},
        "metrics": {"order": 55, "morale": 60, "resources": 80},
        "recent_events": ["Breach sealed", "Storm approaches"],
    }


def test_director_agent_parses_llm_payload() -> None:
    mock_client = MagicMock()
    response_payload = {
        "scene_intent": {
            "focus": "escalate",
            "summary": "Strike before the raiders regroup.",
            "turn": 4,
            "risk_budget": 3,
            "notes": "Weather grants cover.",
        },
        "player_options": [
            {"id": "option_1", "label": "Charge the siege engines", "type": "offense"},
            {"id": "option_2", "label": "Sabotage their bridges", "type": "stealth"},
        ],
    }
    mock_client.generate.return_value = {"response": json.dumps(response_payload)}
    agent = DirectorAgent(llm_client=mock_client)
    projected = _sample_state()
    payload = agent.generate_intent(projected, player_choice="option_2")
    assert payload["scene_intent"]["focus"] == "escalate"
    assert len(payload["player_options"]) == 2
    assert payload["player_options"][0]["label"] == "Charge the siege engines"
    mock_client.generate.assert_called_once()


def test_director_agent_falls_back_on_llm_error() -> None:
    mock_client = MagicMock()
    mock_client.generate.side_effect = OllamaClientError("boom")
    agent = DirectorAgent(llm_client=mock_client)
    projected = _sample_state()
    projected["world"]["stability"] = 30
    payload = agent.generate_intent(projected)
    assert payload["scene_intent"]["focus"] == "stabilize"
    assert len(payload["player_options"]) >= 3
