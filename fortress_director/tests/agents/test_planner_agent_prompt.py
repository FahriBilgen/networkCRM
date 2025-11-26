import json

import pytest
from jsonschema import ValidationError

from fortress_director.agents.planner_agent import PlannerAgent


def sample_projected_state() -> dict:
    return {
        "turn": 5,
        "world": {"stability": 40, "resources": 30, "threat_level": "high"},
        "metrics": {"order": 48, "morale": 44, "resources": 30},
        "flags": ["combat_active"],
        "recent_events": ["Raiders testing the gates."],
        "npc_focus": [{"id": "rhea", "room": "battlements", "hostile": False}],
        "nearby_grid": [],
    }


def sample_scene_intent() -> dict:
    return {
        "focus": "stabilize",
        "summary": "Hold the western wall.",
        "player_choice": "option_1",
    }


def test_build_prompt_lists_relevant_functions() -> None:
    agent = PlannerAgent()
    prompt = agent.build_prompt(sample_projected_state(), sample_scene_intent())
    assert "AVAILABLE_FUNCTIONS" in prompt
    assert "reinforce_wall(structure_id" in prompt
    assert "[combat | gas" in prompt


def test_validate_llm_output_accepts_valid_plan() -> None:
    agent = PlannerAgent()
    payload = json.dumps(
        {
            "gas": 1,
            "calls": [
                {
                    "name": "adjust_metric",
                    "kwargs": {"metric": "order", "delta": 1, "cause": "test"},
                },
            ],
        },
    )
    validated = agent.validate_llm_output(payload)
    assert validated["calls"][0]["name"] == "adjust_metric"


def test_validate_llm_output_rejects_invalid_plan() -> None:
    agent = PlannerAgent()
    bad_payload = json.dumps({"gas": 1})
    with pytest.raises((ValidationError, ValueError)):
        agent.validate_llm_output(bad_payload)


def test_plan_actions_returns_validated_actions() -> None:
    agent = PlannerAgent()
    result = agent.plan_actions(sample_projected_state(), sample_scene_intent())
    assert result["planned_actions"]
    assert "prompt" in result
    for action in result["planned_actions"]:
        assert "function" in action
        assert "args" in action
