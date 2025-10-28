import pytest

from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.llm.offline_client import OfflineOllamaClient
from fortress_director.agents.event_agent import EventAgent
from fortress_director.agents.world_agent import WorldAgent
from fortress_director.agents.character_agent import CharacterAgent
from fortress_director.agents.judge_agent import JudgeAgent


def test_orchestrator_returns_structured_ui_fields(tmp_path):
    """Smoke test: run a single turn with offline LLM clients and verify UI fields."""
    orch = Orchestrator.build_default()

    # Replace live model clients with deterministic offline stubs
    orch.event_agent = EventAgent(client=OfflineOllamaClient(agent_key="event"))
    orch.world_agent = WorldAgent(client=OfflineOllamaClient(agent_key="world"))
    orch.character_agent = CharacterAgent(
        client=OfflineOllamaClient(agent_key="character")
    )
    orch.judge_agent = JudgeAgent(client=OfflineOllamaClient(agent_key="judge"))

    result = orch.run_turn()

    # Basic shape checks for UI-consumed fields
    assert isinstance(result, dict)
    assert "npcs" in result
    assert isinstance(result["npcs"], list)
    assert "safe_function_history" in result
    assert isinstance(result["safe_function_history"], list)
    assert "room_history" in result
    assert isinstance(result["room_history"], list)
