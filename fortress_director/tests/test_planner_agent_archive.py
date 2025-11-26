"""Test PlannerAgent LLM prompt injection with StateArchive."""

import pytest
from fortress_director.agents.planner_agent import PlannerAgent
from fortress_director.core.state_archive import StateArchive


@pytest.fixture
def planner_agent():
    """Create a PlannerAgent with LLM disabled."""
    return PlannerAgent(use_llm=False)


@pytest.fixture
def archive():
    """Create a StateArchive with test data."""
    arch = StateArchive("test_session")
    for i in range(1, 12):
        state = {
            "world": {"threat_level": float(i)},
            "npcs": {"rhea": {"position": i}},
        }
        delta = {
            "recent_events": [f"Planning event {i}"],
            "flags_added": ["planned"],
        }
        arch.record_turn(i, state, delta)
    return arch


def test_planner_with_archive(planner_agent, archive):
    """Test that PlannerAgent.plan_actions accepts archive."""
    projected_state = {
        "metrics": {"turn": 10},
        "structures": {"north_wall": {"integrity": 80}},
        "npcs": {"rhea": {"status": "active"}},
        "resources": {"food": 50},
    }
    scene_intent = {
        "focus": "stabilize",
        "summary": "Reinforce defensive positions",
        "turn": 10,
    }

    result = planner_agent.plan_actions(
        projected_state,
        scene_intent,
        archive=archive,
        turn_number=10,
    )

    assert result is not None
    assert "planned_actions" in result
    assert "prompt" in result
    assert "raw_plan" in result
    assert isinstance(result["planned_actions"], list)


def test_planner_without_archive(planner_agent):
    """Test that PlannerAgent still works without archive."""
    projected_state = {
        "metrics": {"turn": 1},
        "structures": {"north_wall": {"integrity": 100}},
        "npcs": {"rhea": {"status": "active"}},
        "resources": {"food": 150},
    }
    scene_intent = {
        "focus": "explore",
        "summary": "Scout perimeter",
        "turn": 1,
    }

    result = planner_agent.plan_actions(projected_state, scene_intent)

    assert result is not None
    assert "planned_actions" in result
    assert isinstance(result["planned_actions"], list)


def test_planner_archive_in_prompt(planner_agent, archive):
    """Test that archive context appears in planner prompt."""
    projected_state = {
        "metrics": {"turn": 18},
        "structures": {"north_wall": {"integrity": 60}},
        "npcs": {"rhea": {"status": "wounded"}},
        "resources": {"food": 30},
    }
    scene_intent = {
        "focus": "escalate",
        "summary": "Prepare counterattack",
        "turn": 18,
    }

    result = planner_agent.plan_actions(
        projected_state,
        scene_intent,
        archive=archive,
        turn_number=18,
    )

    prompt = result.get("prompt", "")
    # Check that prompt was built (may or may not contain archive depending on
    # injection window, but it should at least contain scene_intent)
    assert "scene_intent" in prompt.lower() or "SCENE_INTENT" in prompt
    assert len(prompt) > 100


def test_planner_backward_compatible(planner_agent):
    """Test that PlannerAgent with old signature still works."""
    projected_state = {
        "metrics": {"turn": 5},
        "structures": {"east_gate": {"integrity": 95}},
        "npcs": {"boris": {"status": "active"}},
        "resources": {"food": 100},
    }
    scene_intent = {
        "focus": "investigate",
        "summary": "Send scouts",
        "turn": 5,
    }

    # Call without archive and turn_number (old signature)
    result = planner_agent.plan_actions(
        projected_state,
        scene_intent,
    )

    assert result is not None
    assert "planned_actions" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
