import pytest

from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from fortress_director.llm.offline_client import OfflineOllamaClient
from fortress_director.agents.event_agent import EventAgent
from fortress_director.agents.world_agent import WorldAgent
from fortress_director.agents.character_agent import CharacterAgent
from fortress_director.agents.creativity_agent import CreativityAgent
from fortress_director.agents.director_agent import DirectorAgent
from fortress_director.agents.judge_agent import JudgeAgent
from fortress_director.agents.planner_agent import PlannerAgent
from fortress_director.codeaware.function_registry import SafeFunctionRegistry
from fortress_director.codeaware.function_validator import (
    FunctionCallValidator,
)
from fortress_director.codeaware.rollback_system import RollbackSystem
from fortress_director.rules.rules_engine import RulesEngine


def test_orchestrator_returns_structured_ui_fields(tmp_path):
    """Smoke test: offline LLM turn verifies UI fields.

    We build a fresh Orchestrator wired to a temporary StateStore so any repo
    persisted 'end' or finalized flags don't short-circuit the turn and the
    code paths that populate the structured UI fields run deterministically.
    """
    # Build an orchestrator wired to a temporary world_state to avoid
    # persisted final/end state from the repo interfering with this smoke run.
    state_store = StateStore(tmp_path / "world_state.json")
    registry = SafeFunctionRegistry()
    validator = FunctionCallValidator(
        registry, max_calls_per_function=5, max_total_calls=20
    )
    rollback = RollbackSystem(
        snapshot_provider=state_store.snapshot,
        restore_callback=state_store.persist,
        max_checkpoints=3,
    )
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    orch = Orchestrator(
        state_store=state_store,
        event_agent=EventAgent(client=OfflineOllamaClient(agent_key="event")),
        world_agent=WorldAgent(client=OfflineOllamaClient(agent_key="world")),
        character_agent=CharacterAgent(
            client=OfflineOllamaClient(agent_key="character")
        ),
        creativity_agent=CreativityAgent(
            client=OfflineOllamaClient(agent_key="creativity"),
            use_llm=False,
        ),
        planner_agent=PlannerAgent(client=OfflineOllamaClient(agent_key="planner")),
        director_agent=DirectorAgent(client=OfflineOllamaClient(agent_key="director")),
        judge_agent=JudgeAgent(client=OfflineOllamaClient(agent_key="judge")),
        rules_engine=RulesEngine(judge_agent=JudgeAgent(), tolerance=1),
        function_registry=registry,
        function_validator=validator,
        rollback_system=rollback,
        runs_dir=runs_dir,
    )
    # Ensure default safe functions are registered for the run
    orch._register_default_safe_functions()

    result = orch.run_turn()

    # Basic shape checks for UI-consumed fields
    assert isinstance(result, dict)
    assert "npcs" in result
    assert isinstance(result["npcs"], list)
    assert "safe_function_history" in result
    assert isinstance(result["safe_function_history"], list)
    assert "room_history" in result
    assert isinstance(result["room_history"], list)

    # Detailed structure validation for UI data contracts
    # Validate npcs structure
    for npc in result["npcs"]:
        assert isinstance(npc, dict)
        assert "name" in npc
        assert "trust" in npc
        assert "summary" in npc
        assert isinstance(npc["name"], str)
        assert isinstance(npc["trust"], int)
        assert isinstance(npc["summary"], str)

    # Validate safe_function_history structure
    for func_result in result["safe_function_history"]:
        assert isinstance(func_result, dict)
        assert "name" in func_result
        assert "success" in func_result
        assert "timestamp" in func_result
        assert "metadata" in func_result
        assert isinstance(func_result["name"], str)
        assert isinstance(func_result["success"], bool)
        # timestamp can be None or str/datetime
        assert isinstance(func_result["metadata"], dict)

    # Validate room_history structure
    for room_entry in result["room_history"]:
        assert isinstance(room_entry, dict)
        assert "room" in room_entry
        assert "turn" in room_entry
        assert "description" in room_entry
        assert isinstance(room_entry["room"], str)
        assert isinstance(room_entry["turn"], int)
        assert isinstance(room_entry["description"], str)
