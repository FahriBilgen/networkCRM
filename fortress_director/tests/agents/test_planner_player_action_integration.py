import json
from unittest.mock import MagicMock

from fortress_director.agents.planner_agent import PlannerAgent
from fortress_director.core import (
    player_action_catalog,
    player_action_router,
    player_action_validator,
)
from fortress_director.core.state_store import GameState
from fortress_director.llm.runtime_mode import set_llm_enabled


def test_planner_includes_required_calls():
    gs = GameState()
    catalog_entry = player_action_catalog.get_action_by_id("repair_wall")
    params = {"structure_id": "western_wall", "amount": 2}
    validated = player_action_validator.validate_player_action("repair_wall", params, gs)
    routed = player_action_router.route_player_action(
        "repair_wall", validated, catalog_entry
    )

    planner = PlannerAgent(use_llm=False)
    projected = gs.get_projected_state()
    plan = planner.plan_actions(
        projected, scene_intent={}, player_action_context=routed
    )
    funcs = [a["function"] for a in plan.get("planned_actions", [])]
    assert "reinforce_wall" in funcs


def test_planner_injects_required_calls_into_plan() -> None:
    set_llm_enabled(True)
    mock_client = MagicMock()
    mock_client.generate.return_value = {
        "response": json.dumps(
            {
                "gas": 1,
                "calls": [
                    {
                        "name": "adjust_metric",
                        "kwargs": {"metric": "order", "delta": 1},
                    },
                ],
            },
        ),
    }
    planner = PlannerAgent(llm_client=mock_client)
    projected_state = GameState().get_projected_state()
    scene_intent = {"focus": "stabilize"}
    context = {
        "player_intent": "move npc scout_ila",
        "required_calls": [
            {
                "function": "move_npc",
                "args": {"npc_id": "scout_ila", "x": 3, "y": 4},
            },
        ],
    }
    result = planner.plan_actions(
        projected_state, scene_intent, player_action_context=context
    )
    functions = [action["function"] for action in result["planned_actions"]]
    assert "move_npc" in functions
