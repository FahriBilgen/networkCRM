"""Test glitch triggered_loss integration with win/loss system."""

import pytest
from fortress_director.orchestrator.orchestrator import Orchestrator
from fortress_director.utils.glitch_manager import GlitchManager


def test_glitch_triggered_loss_integration(orchestrator: Orchestrator) -> None:
    """Test that triggered_loss from glitch manager affects win/loss evaluation."""
    # Setup a state with high glitch that would trigger loss
    state = orchestrator.state_store.snapshot()
    state["metrics"]["glitch"] = 95  # Above threshold
    orchestrator.state_store.persist(state)

    # Mock glitch manager to return triggered_loss=True
    original_resolve_glitch = orchestrator.glitch_manager.resolve_glitch

    def mock_resolve_glitch(turn, seed):
        return {"roll": 85, "effects": ["Test glitch effect"], "triggered_loss": True}

    orchestrator.glitch_manager.resolve_glitch = mock_resolve_glitch

    try:
        # Run a turn - this should trigger loss due to glitch
        result = orchestrator.run_turn(player_choice_id="1")

        # Check that win/loss status is loss due to glitch_overload
        assert result["win_loss"]["status"] == "loss"
        assert result["win_loss"]["reason"] == "glitch_overload"

    finally:
        # Restore original method
        orchestrator.glitch_manager.resolve_glitch = original_resolve_glitch


def test_glitch_triggered_loss_override_ongoing(orchestrator: Orchestrator) -> None:
    """Test that triggered_loss overrides ongoing status."""
    # Setup state with metrics that would normally be ongoing
    state = orchestrator.state_store.snapshot()
    state["metrics"]["glitch"] = 50  # Not high enough for automatic loss
    state["metrics"]["order"] = 50
    state["metrics"]["morale"] = 50
    orchestrator.state_store.persist(state)

    # Mock glitch to trigger loss
    original_resolve_glitch = orchestrator.glitch_manager.resolve_glitch

    def mock_resolve_glitch(turn, seed):
        return {"roll": 85, "effects": ["Test glitch effect"], "triggered_loss": True}

    orchestrator.glitch_manager.resolve_glitch = mock_resolve_glitch

    try:
        result = orchestrator.run_turn(player_choice_id="1")

        # Should be loss despite otherwise ongoing metrics
        assert result["win_loss"]["status"] == "loss"
        assert result["win_loss"]["reason"] == "glitch_overload"

    finally:
        orchestrator.glitch_manager.resolve_glitch = original_resolve_glitch
