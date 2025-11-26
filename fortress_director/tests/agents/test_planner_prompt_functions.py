from __future__ import annotations

from fortress_director.agents.planner_agent import PlannerAgent
from fortress_director.core.function_registry import load_defaults


SAMPLE_STATE = {
    "turn": 1,
    "world": {"stability": 50, "resources": 40},
    "metrics": {"order": 60, "morale": 55, "resources": 40},
    "flags": [],
    "recent_events": [],
}

SAMPLE_INTENT = {"focus": "stabilize", "summary": "Hold the gate."}


def test_planner_prompt_lists_all_functions() -> None:
    agent = PlannerAgent()
    prompt = agent.build_prompt(SAMPLE_STATE, SAMPLE_INTENT)
    registry = load_defaults()
    for name in registry:
        assert name in prompt, f"missing function name in prompt: {name}"
