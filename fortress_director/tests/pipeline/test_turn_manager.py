from unittest.mock import Mock

from fortress_director.core.state_store import GameState
from fortress_director.llm.runtime_mode import set_llm_enabled
from fortress_director.pipeline.turn_manager import TurnManager, run_turn

set_llm_enabled(False)


def test_turn_manager_orders_dependencies():
    initial_state = {
        "turn": 0,
        "world": {"stability": 40, "resources": 70, "threat_level": "high"},
        "log": [],
    }
    game_state = GameState(initial_state)
    director = Mock()
    director.generate_intent.return_value = {
        "scene_intent": {"focus": "explore"},
        "player_options": [],
    }
    planner = Mock()
    planner.plan_actions.return_value = {
        "planned_actions": [{"function": "noop", "args": {}}],
    }
    executor = Mock()
    executor.apply_actions.return_value = {
        "world_state": {"turn": 1, "world": {}},
        "executed_actions": [{"function": "noop", "log": "done"}],
        "state_delta": {"turn_advanced": True},
    }
    renderer = Mock()
    renderer.render.return_value = {
        "narrative_block": "story",
        "npc_dialogues": [],
        "atmosphere": {"mood": "calm"},
    }
    manager = TurnManager(
        director_agent=director,
        planner_agent=planner,
        world_renderer_agent=renderer,
        function_executor_module=executor,
    )
    result = manager.run_turn(game_state, player_choice={"id": "option_1"})
    assert result.narrative == "story"
    director.generate_intent.assert_called_once()
    planner.plan_actions.assert_called_once()
    executor.apply_actions.assert_called_once()
    renderer.render.assert_called_once()


def test_default_run_turn_produces_payload():
    result = run_turn(GameState(), player_choice={"id": "option_1"})
    assert result.state_delta["turn_advanced"]
    assert result.narrative
    assert result.ui_events
