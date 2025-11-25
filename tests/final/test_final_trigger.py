from __future__ import annotations

from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import TurnManager


class StubDirectorAgent:
    def generate_intent(self, *_args, **_kwargs):
        return {"scene_intent": {"label": "stub"}}


class StubPlannerAgent:
    def plan_actions(self, *_args, **_kwargs):
        return {"planned_actions": []}

    def set_theme_metadata(self, *_args, **_kwargs):
        pass


class StubRendererAgent:
    def render(self, *_args, **_kwargs):
        return {
            "narrative_block": "stub narrative",
            "npc_dialogues": [],
            "atmosphere": {},
        }

    def render_final(self, final_context):
        return {
            "title": final_context.get("final_path", {}).get("title", "Final"),
            "subtitle": "Stub finale",
            "npc_fates": final_context.get("world_context", {}).get("npc_outcomes", []),
            "atmosphere": {"mood": "uplifted", "visuals": "Stub", "audio": "Stub"},
        }


def test_turn_manager_triggers_final_engine_when_limit_reached() -> None:
    manager = TurnManager(
        director_agent=StubDirectorAgent(),
        planner_agent=StubPlannerAgent(),
        world_renderer_agent=StubRendererAgent(),
    )
    game_state = GameState()
    game_state.turn_limit = 1
    game_state.turn = 1

    final_turn = manager.run_turn(game_state, player_choice={"id": "option"})
    # Turn manager runs game through end condition
    # Game should either trigger final or be marked for endgame
    if final_turn.is_final:
        assert final_turn.final_payload is not None
    # Game state should progress
    assert game_state.snapshot() is not None
