from fortress_director.agents import (DirectorAgent, PlannerAgent,
                                      WorldRendererAgent)
from fortress_director.core.state_store import GameState


def test_director_agent_generates_intent_with_options():
    agent = DirectorAgent(use_llm=False)
    projected = {
        "turn": 2,
        "world": {"stability": 40, "resources": 50, "threat_level": "high"},
    }
    payload = agent.generate_intent(projected, player_choice="option_2")
    assert payload["scene_intent"]["focus"] == "stabilize"
    assert payload["scene_intent"]["player_choice"] == "option_2"
    assert len(payload["player_options"]) >= 2


def test_planner_agent_emits_actions():
    planner = PlannerAgent(use_llm=False)
    projected = GameState().get_projected_state()
    scene_intent = {"focus": "explore", "summary": "Scout."}
    payload = planner.plan_actions(projected, scene_intent)
    assert payload["planned_actions"]
    assert all("function" in action for action in payload["planned_actions"])


def test_world_renderer_returns_narrative():
    renderer = WorldRendererAgent(use_llm=False)
    world_state = {
        "turn": 3,
        "world": {"stability": 65, "resources": 90},
    }
    executed_actions = [{"function": "adjust", "args": {}, "status": "applied"}]
    payload = renderer.render(world_state, executed_actions)
    assert "Turn 3" in payload["narrative_block"]
    assert payload["npc_dialogues"]
    assert payload["atmosphere"]["mood"] in {"resolute", "tense"}
