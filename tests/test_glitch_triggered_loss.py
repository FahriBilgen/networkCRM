"""Test glitch triggered_loss integration with real AI."""

import pytest
import os
from pathlib import Path
from fortress_director.orchestrator.orchestrator import Orchestrator, StateStore


@pytest.fixture
def orchestrator(tmp_path: Path) -> Orchestrator:
    """Create orchestrator for testing."""
    # Create orchestrator with runs_dir
    orchestrator = Orchestrator.__new__(Orchestrator)
    from fortress_director.agents.event_agent import EventAgent
    from fortress_director.agents.world_agent import WorldAgent
    from fortress_director.agents.character_agent import CharacterAgent
    from fortress_director.agents.judge_agent import JudgeAgent
    from fortress_director.rules.rules_engine import RulesEngine
    from fortress_director.codeaware.function_registry import SafeFunctionRegistry
    from fortress_director.codeaware.function_validator import FunctionCallValidator
    from fortress_director.codeaware.rollback_system import RollbackSystem

    state_store = StateStore(tmp_path / "world_state.json")
    orchestrator.state_store = state_store
    orchestrator.event_agent = EventAgent()
    orchestrator.world_agent = WorldAgent()
    orchestrator.character_agent = CharacterAgent()
    orchestrator.judge_agent = JudgeAgent()
    rules_engine = RulesEngine(judge_agent=orchestrator.judge_agent)
    orchestrator.rules_engine = rules_engine
    orchestrator.function_registry = SafeFunctionRegistry()
    function_validator = FunctionCallValidator(
        orchestrator.function_registry, max_calls_per_function=5, max_total_calls=20
    )
    orchestrator.function_validator = function_validator
    rollback_system = RollbackSystem(
        snapshot_provider=state_store.snapshot,
        restore_callback=state_store.persist,
        max_checkpoints=3,
    )
    orchestrator.rollback_system = rollback_system
    runs_dir = tmp_path / "runs" / "latest_run"
    runs_dir.mkdir(parents=True, exist_ok=True)
    orchestrator.runs_dir = runs_dir
    orchestrator._register_default_safe_functions()

    return orchestrator


@pytest.mark.integration
def test_glitch_triggered_loss_integration_real_ai(orchestrator: Orchestrator) -> None:
    """Test glitch triggered_loss with real AI models."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip("Skipping real AI test; set FORTRESS_USE_OLLAMA=1 to run")

    # Setup a state with high glitch that would trigger loss
    state = orchestrator.state_store.snapshot()
    state["metrics"]["glitch"] = 95  # Above threshold
    orchestrator.state_store.persist(state)

    # Run a turn - should trigger loss due to high glitch
    result = orchestrator.run_turn(player_choice_id="1")

    # Check that win/loss status is loss due to glitch_overload
    assert result["win_loss"]["status"] == "loss"
    assert result["win_loss"]["reason"] == "system_glitch"


@pytest.mark.integration
def test_glitch_triggered_loss_override_ongoing_real_ai(
    orchestrator: Orchestrator,
) -> None:
    """Test that high glitch triggers loss with real AI."""
    if os.environ.get("FORTRESS_USE_OLLAMA") != "1":
        pytest.skip("Skipping real AI test; set FORTRESS_USE_OLLAMA=1 to run")

    # Setup state with high glitch that triggers automatic loss
    state = orchestrator.state_store.snapshot()
    state["metrics"]["glitch"] = 95  # Above threshold for automatic loss
    state["metrics"]["order"] = 50
    state["metrics"]["morale"] = 50
    orchestrator.state_store.persist(state)

    # Run a turn - should trigger loss due to high glitch
    result = orchestrator.run_turn(player_choice_id="1")

    # Should be loss despite otherwise ongoing metrics
    assert result["win_loss"]["status"] == "loss"
    assert result["win_loss"]["reason"] == "system_glitch"
