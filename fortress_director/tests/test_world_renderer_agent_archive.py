"""Test WorldRendererAgent LLM prompt injection with StateArchive."""

import pytest
from fortress_director.agents.world_renderer_agent import WorldRendererAgent
from fortress_director.core.state_archive import StateArchive


@pytest.fixture
def world_renderer():
    """Create a WorldRendererAgent with LLM disabled."""
    return WorldRendererAgent(use_llm=False)


@pytest.fixture
def archive():
    """Create a StateArchive with test data."""
    arch = StateArchive("test_session")
    for i in range(1, 12):
        state = {
            "world": {"atmosphere": "tense"},
            "structures": {"north_wall": {"integrity": 100 - (i * 5)}},
        }
        delta = {
            "recent_events": [f"Narrative event {i}"],
            "flags_added": ["rendered"],
        }
        arch.record_turn(i, state, delta)
    return arch


def test_renderer_with_archive(world_renderer, archive):
    """Test that WorldRendererAgent.render accepts archive."""
    world_state = {
        "turn": 10,
        "atmosphere": "tense",
        "structures": {"north_wall": {"integrity": 50}},
        "npcs": {"ila": {"status": "active"}},
    }
    executed_actions = [
        {
            "function": "reinforce_wall",
            "args": {"structure_id": "north_wall", "amount": 2},
        }
    ]

    result = world_renderer.render(
        world_state,
        executed_actions,
        threat_phase="rising",
        event_seed="battle",
        archive=archive,
        turn_number=10,
    )

    assert result is not None
    assert "narrative_block" in result
    assert "npc_dialogues" in result
    assert "atmosphere" in result
    assert isinstance(result["narrative_block"], str)
    assert len(result["narrative_block"]) > 0


def test_renderer_without_archive(world_renderer):
    """Test that WorldRendererAgent still works without archive."""
    world_state = {
        "turn": 1,
        "atmosphere": "calm",
        "structures": {"north_wall": {"integrity": 100}},
        "npcs": {"ila": {"status": "active"}},
    }
    executed_actions = []

    result = world_renderer.render(
        world_state,
        executed_actions,
        threat_phase="calm",
    )

    assert result is not None
    assert "narrative_block" in result
    assert isinstance(result["narrative_block"], str)
    assert len(result["narrative_block"]) > 0


def test_renderer_archive_in_prompt(world_renderer, archive):
    """Test that archive context appears in renderer prompt."""
    world_state = {
        "turn": 18,
        "atmosphere": "dire",
        "structures": {"north_wall": {"integrity": 20}},
        "npcs": {"ila": {"status": "wounded"}},
    }
    executed_actions = [
        {
            "function": "send_on_patrol",
            "args": {"npc_id": "ila", "duration": 2},
        }
    ]

    result = world_renderer.render(
        world_state,
        executed_actions,
        threat_phase="peak",
        event_seed="sabotage",
        archive=archive,
        turn_number=18,
    )

    # Result should contain narrative rendering
    assert result is not None
    assert "narrative_block" in result
    assert len(result["narrative_block"]) > 0
    # Atmosphere should be present
    assert "atmosphere" in result


def test_renderer_backward_compatible(world_renderer):
    """Test that WorldRendererAgent with old signature still works."""
    world_state = {
        "turn": 5,
        "atmosphere": "tense",
        "structures": {"east_gate": {"integrity": 85}},
    }
    executed_actions = []

    # Call without archive and turn_number (old signature)
    result = world_renderer.render(
        world_state,
        executed_actions,
        threat_phase="rising",
    )

    assert result is not None
    assert "narrative_block" in result
    assert isinstance(result["narrative_block"], str)


def test_renderer_with_combat_actions(world_renderer, archive):
    """Test renderer with combat-related executed actions."""
    world_state = {
        "turn": 15,
        "atmosphere": "violent",
        "structures": {"north_wall": {"integrity": 40}},
        "npcs": {"rhea": {"status": "fighting"}},
    }
    executed_actions = [
        {"function": "move_npc", "args": {"npc_id": "rhea", "x": 5, "y": 3}},
        {
            "function": "spawn_event_marker",
            "args": {"marker_id": "battle_01", "x": 5, "y": 3},
        },
    ]

    result = world_renderer.render(
        world_state,
        executed_actions,
        threat_phase="peak",
        event_seed="battle",
        archive=archive,
        turn_number=15,
    )

    assert result is not None
    assert "narrative_block" in result
    # Should have rendered the combat scenario
    assert len(result["narrative_block"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
