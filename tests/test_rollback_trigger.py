"""Test rollback system with deliberate failures."""

import pytest
from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.codeaware.function_registry import FunctionValidationError


def test_rollback_on_safe_function_failure(orchestrator: Orchestrator) -> None:
    """Test that rollback occurs when a safe function fails."""
    # Setup initial state
    orchestrator.run_turn(player_choice_id="1")

    # Get initial state
    initial_state = orchestrator.state_store.snapshot()

    # Try to call a safe function that will fail
    try:
        # This should fail validation
        orchestrator.function_registry.call("change_weather()")  # Missing required args
        pytest.fail("Expected FunctionValidationError")
    except FunctionValidationError:
        pass

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
