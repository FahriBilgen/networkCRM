import json
from unittest.mock import MagicMock

from fortress_director.agents import WorldRendererAgent
from fortress_director.llm.ollama_client import OllamaClientError


def _sample_world_state() -> dict:
    return {
        "turn": 7,
        "world": {"stability": 58, "resources": 70, "threat_level": "tense"},
        "metrics": {"order": 55, "morale": 60, "corruption": 12},
        "log": ["Engineers reinforced the breach."],
    }


def test_world_renderer_agent_parses_llm_response() -> None:
    mock_client = MagicMock()
    response_payload = {
        "narrative_block": "The walls groaned but held as scouts dashed back.",
        "npc_dialogues": [
            {"speaker": "Scout Ila", "line": "Tracks fade where the fog thickens."},
        ],
        "atmosphere": {"mood": "tense", "visuals": "Fog clings to the ramparts."},
    }
    mock_client.generate.return_value = {"response": json.dumps(response_payload)}
    renderer = WorldRendererAgent(llm_client=mock_client)
    payload = renderer.render(
        _sample_world_state(),
        [{"function": "adjust_metric", "args": {"metric": "order"}}],
    )
    assert payload["narrative_block"].startswith("The walls groaned")
    assert payload["npc_dialogues"][0]["speaker"] == "Scout Ila"
    assert payload["atmosphere"]["mood"] == "tense"
    mock_client.generate.assert_called_once()


def test_world_renderer_agent_uses_fallback_on_error() -> None:
    mock_client = MagicMock()
    mock_client.generate.side_effect = OllamaClientError("offline")
    renderer = WorldRendererAgent(llm_client=mock_client)
    payload = renderer.render(_sample_world_state(), [])
    assert "Turn 7" in payload["narrative_block"]
    assert payload["npc_dialogues"]


def test_world_renderer_fills_missing_atmosphere_fields() -> None:
    mock_client = MagicMock()
    response_payload = {
        "narrative_block": "Watchers report limited movement on the ridge.",
        "npc_dialogues": [
            {"speaker": "Scout Ila", "line": "Rain muffled their torches."}
        ],
        "atmosphere": {},
    }
    mock_client.generate.return_value = {"response": json.dumps(response_payload)}
    renderer = WorldRendererAgent(llm_client=mock_client)
    executed = [
        {"function": "reinforce_wall", "args": {"structure_id": "outer_wall", "amount": 1}}
    ]
    payload = renderer.render(_sample_world_state(), executed)
    atmosphere = payload["atmosphere"]
    assert atmosphere["mood"] in {"tense", "grim", "hopeful"}
    assert atmosphere["visuals"]
    assert atmosphere["audio"]


def test_world_renderer_keeps_llm_atmosphere_when_present() -> None:
    mock_client = MagicMock()
    response_payload = {
        "narrative_block": "The plaza glows as braziers roar awake.",
        "npc_dialogues": [
            {"speaker": "Quartermaster Lysa", "line": "Stockpiles look steady tonight."}
        ],
        "atmosphere": {
            "mood": "calm",
            "visuals": "Lanterns halo the inner courtyard.",
            "audio": "Quiet chanting echoes beneath the keep.",
        },
    }
    mock_client.generate.return_value = {"response": json.dumps(response_payload)}
    renderer = WorldRendererAgent(llm_client=mock_client)
    payload = renderer.render(_sample_world_state(), [{"function": "adjust_metric"}])
    assert payload["atmosphere"]["mood"] == "calm"
    assert payload["atmosphere"]["visuals"] == "Lanterns halo the inner courtyard."
    assert payload["atmosphere"]["audio"] == "Quiet chanting echoes beneath the keep."
