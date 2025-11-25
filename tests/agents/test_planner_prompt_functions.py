from fortress_director.agents.planner_agent import PlannerAgent


def test_build_prompt_contains_available_functions():
    agent = PlannerAgent(use_llm=False)
    projected = {"turn": 1}
    scene_intent = {"summary": "test"}
    prompt = agent.build_prompt(projected, scene_intent)
    assert "AVAILABLE_FUNCTIONS:" in prompt
    # The prompt should contain at least one function signature line
    assert "- " in prompt
