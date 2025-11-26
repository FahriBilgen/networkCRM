from __future__ import annotations

import json

import pytest

from fortress_director.agents.planner_agent import PlannerAgent


@pytest.fixture
def agent() -> PlannerAgent:
    return PlannerAgent()


def test_validate_llm_output_rejects_missing_required_param(agent: PlannerAgent) -> None:
    payload = json.dumps(
        {
            "gas": 1,
            "calls": [
                {
                    "name": "move_npc",
                    "kwargs": {"npc_id": "ila", "x": 2},
                }
            ],
        }
    )
    with pytest.raises(ValueError):
        agent.validate_llm_output(payload)


def test_validate_llm_output_rejects_extra_param(agent: PlannerAgent) -> None:
    payload = json.dumps(
        {
            "gas": 1,
            "calls": [
                {
                    "name": "reinforce_wall",
                    "kwargs": {
                        "structure_id": "wall",
                        "amount": 2,
                        "unknown": 5,
                    },
                }
            ],
        }
    )
    with pytest.raises(ValueError):
        agent.validate_llm_output(payload)


def test_validate_llm_output_accepts_valid_new_function(agent: PlannerAgent) -> None:
    payload = json.dumps(
        {
            "gas": 1,
            "calls": [
                {
                    "name": "reinforce_wall",
                    "kwargs": {"structure_id": "wall", "amount": 2},
                }
            ],
        }
    )
    result = agent.validate_llm_output(payload)
    assert result["calls"][0]["name"] == "reinforce_wall"
