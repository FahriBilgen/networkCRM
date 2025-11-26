"""Test DirectorAgent LLM prompt injection with StateArchive."""

import pytest
from fortress_director.agents.director_agent import DirectorAgent
from fortress_director.core.state_archive import StateArchive
from fortress_director.core.threat_model import ThreatSnapshot


@pytest.fixture
def director_agent():
    """Create a DirectorAgent with LLM disabled."""
    return DirectorAgent(use_llm=False)


@pytest.fixture
def archive():
    """Create a StateArchive with test data."""
    arch = StateArchive("test_session")
    for i in range(1, 12):
        state = {"world": {"threat_level": float(i)}}
        delta = {
            "recent_events": [f"Major event {i}"],
            "flags_added": ["flag"],
        }
        arch.record_turn(i, state, delta)
    return arch


def test_director_with_archive(director_agent, archive):
    """Test that DirectorAgent.generate_intent accepts archive."""
    projected_state = {
        "metrics": {"turn": 10},
        "recent_events": ["Test event"],
        "npc_locations": [],
    }
    threat_snapshot = ThreatSnapshot(
        base_threat=3,
        escalation=0.5,
        morale=70,
        resources=100,
        recent_hostility=2,
        turn=10,
        threat_score=5.0,
        phase="rising",
    )

    result = director_agent.generate_intent(
        projected_state,
        player_choice="option_1",
        threat_snapshot=threat_snapshot,
        archive=archive,
        turn_number=10,
    )

    assert result is not None
    assert "scene_intent" in result
    assert "player_options" in result


def test_director_without_archive(director_agent):
    """Test that DirectorAgent still works without archive."""
    projected_state = {
        "metrics": {"turn": 1},
        "recent_events": [],
        "npc_locations": [],
    }
    threat_snapshot = ThreatSnapshot(
        base_threat=1,
        escalation=0.0,
        morale=80,
        resources=150,
        recent_hostility=0,
        turn=1,
        threat_score=1.0,
        phase="calm",
    )

    result = director_agent.generate_intent(
        projected_state,
        threat_snapshot=threat_snapshot,
    )

    assert result is not None
    assert "scene_intent" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
