import pytest

from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore
from fortress_director.llm.ollama_client import OllamaClient
from fortress_director.agents.base_agent import default_ollama_client
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


def test_orchestrator_with_real_models(tmp_path):
    """Integration test: run a turn with real Ollama models.

    This test ensures that:
    1. Ollama models are accessible and responding
    2. Agent integration works with real models
    3. Turn execution completes successfully
    4. UI data contracts are maintained with real models
    """
    # Build an orchestrator with real Ollama models
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

    # Use configured Ollama clients (Settings/env) to avoid short timeouts
    c_event = default_ollama_client("event")
    c_world = default_ollama_client("world")
    c_character = default_ollama_client("character")
    c_judge = default_ollama_client("judge")
    c_creativity = default_ollama_client("creativity")
    c_planner = default_ollama_client("planner")
    c_director = default_ollama_client("director")

    orch = Orchestrator(
        state_store=state_store,
        event_agent=EventAgent(client=c_event),
        world_agent=WorldAgent(client=c_world),
        character_agent=CharacterAgent(client=c_character),
        creativity_agent=CreativityAgent(client=c_creativity),
        planner_agent=PlannerAgent(client=c_planner),
        director_agent=DirectorAgent(client=c_director),
        judge_agent=JudgeAgent(client=c_judge),
        rules_engine=RulesEngine(judge_agent=JudgeAgent(client=c_judge), tolerance=1),
        function_registry=registry,
        function_validator=validator,
        rollback_system=rollback,
        runs_dir=runs_dir,
    )

    # Ensure default safe functions are registered
    orch._register_default_safe_functions()

    # Run one turn with real models
    result = orch.run_turn()

    # Verify basic structure
    assert isinstance(result, dict)
    assert "npcs" in result
    assert "safe_function_history" in result
    assert "room_history" in result

    # Verify UI data contracts are maintained
    assert isinstance(result["npcs"], list)
    assert isinstance(result["safe_function_history"], list)
    assert isinstance(result["room_history"], list)

    # Verify at least one NPC is present
    assert len(result["npcs"]) > 0

    # Verify turn completed (should have some history)
    assert len(result["room_history"]) > 0

    print("Real model test completed successfully!")
    print(f"NPCs: {len(result['npcs'])}")
    print(f"Safe functions executed: {len(result['safe_function_history'])}")
    print(f"Room history entries: {len(result['room_history'])}")
