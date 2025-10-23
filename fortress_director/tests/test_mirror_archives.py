"""Test script for The Mirror Archives scenario."""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fortress_director.orchestrator.orchestrator import Orchestrator


def test_initial_state():
    """Test initial world state."""
    orchestrator = Orchestrator.build_default()
    state = orchestrator.state_store.snapshot()
    print("Initial state:")
    print(json.dumps(state, indent=2))

    # Check required keys
    required = [
        "campaign_id",
        "turn_limit",
        "current_turn",
        "scores",
        "flags",
        "memory_layers",
        "active_layer",
        "npc_fragments",
        "inventory",
        "lore",
    ]
    for key in required:
        assert key in state, f"Missing {key}"
    print("✓ Initial state valid")


def test_run_turn():
    """Test running a turn."""
    orchestrator = Orchestrator.build_default()

    # Run first turn without choice
    result = orchestrator.run_turn()
    print("Turn 1 result:")
    print(json.dumps(result, indent=2))

    # Check result structure
    assert "WORLD_CONTEXT" in result
    assert "scene" in result
    assert "options" in result
    assert len(result["options"]) == 3
    print("✓ Turn execution successful")


def test_safe_functions():
    """Test safe functions."""
    orchestrator = Orchestrator.build_default()

    # Test adjust_logic
    result = orchestrator.function_registry.call("adjust_logic")
    print("adjust_logic result:", result)
    assert "scores" in result

    # Test advance_turn
    result = orchestrator.function_registry.call("advance_turn")
    print("advance_turn result:", result)
    assert "current_turn" in result
    print("✓ Safe functions work")


def test_ending_conditions():
    """Test ending conditions."""
    orchestrator = Orchestrator.build_default()

    # Set turn to limit
    state = orchestrator.state_store.snapshot()
    state["current_turn"] = 10
    orchestrator.state_store.persist(state)

    result = orchestrator.run_turn()
    print("Ending result:")
    print(json.dumps(result, indent=2))

    # Should be final scene
    assert "scene" in result
    assert len(result.get("options", [])) == 0
    print("✓ Ending conditions work")


if __name__ == "__main__":
    print("Testing The Mirror Archives...")
    test_initial_state()
    test_run_turn()
    test_safe_functions()
    test_ending_conditions()
    print("All tests passed! 🎉")
