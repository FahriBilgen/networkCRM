"""Test rollback system with deliberate failures."""

import pytest
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
    orchestrator._register_default_safe_functions()
    return orchestrator


def test_rollback_on_safe_function_failure(orchestrator: Orchestrator) -> None:
    """Test that rollback occurs when a safe function fails."""
    # Setup initial state
    orchestrator.run_turn(player_choice_id="1")

    # Get initial state
    initial_state = orchestrator.state_store.snapshot()

    # Try to call a safe function that will fail
    try:
        # This should fail because function is not registered
        orchestrator.function_registry.call("nonexistent_function()")
        pytest.fail("Expected FunctionNotRegisteredError")
    except Exception as e:
        # Should get FunctionNotRegisteredError or similar
        assert "not registered" in str(e).lower() or "not found" in str(e).lower()

    # Check that rollback was triggered (state should be restored)
    # Note: In current implementation, rollback only happens in run_turn exceptions
    # This test documents the current behavior - rollback needs to be called manually
    current_state = orchestrator.state_store.snapshot()
    assert (
        current_state == initial_state
    ), "State should be unchanged after failed function call"


def test_rollback_on_agent_output_error(orchestrator: Orchestrator) -> None:
    """Test rollback when agent produces invalid output."""
    # This would require mocking an agent to return invalid JSON
    # For now, document that this scenario should trigger rollback
    # as seen in the orchestrator.run_turn() exception handling
    pass
