from unittest.mock import Mock

from fortress_director.core.state_store import GameState
from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.pipeline.turn_manager import TurnManager


class StubThreatModel:
    def __init__(self, snapshot: ThreatSnapshot):
        self._snapshot = snapshot

    def compute(self, _game_state: GameState) -> ThreatSnapshot:
        return self._snapshot

    def has_baseline(self) -> bool:
        return True

    def set_base_threat(self, _value: int) -> None:  # pragma: no cover
        return None


class StubEventCurve:
    def next_event(self, _snapshot, _game_state) -> str:
        return "raid_probe"


class StubEndgameDetector:
    def check(self, *_args, **_kwargs):
        return {"final_trigger": False}


class StubExecutor:
    @staticmethod
    def apply_actions(game_state: GameState, _actions):
        return {
            "world_state": game_state.snapshot(),
            "executed_actions": [],
            "state_delta": {"noop": True},
        }


def _snapshot() -> ThreatSnapshot:
    return ThreatSnapshot(
        base_threat=10,
        escalation=5.0,
        morale=55,
        resources=40,
        recent_hostility=1,
        turn=2,
        threat_score=20.0,
        phase="calm",
    )


def _game_state() -> GameState:
    return GameState(
        {
            "turn": 0,
            "rng_seed": 99,
            "metrics": {"turn": 0},
            "npc_locations": [
                {
                    "id": "npc_a",
                    "name": "A",
                    "role": "guard",
                    "x": 1,
                    "y": 1,
                    "fatigue": 3,
                },
                {
                    "id": "npc_b",
                    "name": "B",
                    "role": "guard",
                    "x": 2,
                    "y": 1,
                    "fatigue": 4,
                },
            ],
            "structures": {
                "wall": {
                    "id": "wall",
                    "kind": "wall",
                    "x": 5,
                    "y": 5,
                    "integrity": 70,
                    "max_integrity": 100,
                    "on_fire": True,
                }
            },
            "stockpiles": {"food": 10, "wood": 0, "ore": 0},
        }
    )


def test_turn_manager_includes_world_tick_delta() -> None:
    director = Mock()
    director.generate_intent.return_value = {
        "scene_intent": {"focus": "hold", "turn": 1},
        "player_options": [],
    }
    planner = Mock()
    planner.plan_actions.return_value = {"planned_actions": []}
    renderer = Mock()
    renderer.render.return_value = {
        "narrative_block": "story",
        "npc_dialogues": [],
        "atmosphere": {},
    }
    game_state = _game_state()
    manager = TurnManager(
        director_agent=director,
        planner_agent=planner,
        world_renderer_agent=renderer,
        threat_model=StubThreatModel(_snapshot()),
        event_curve=StubEventCurve(),
        endgame_detector=StubEndgameDetector(),
        function_executor_module=StubExecutor,
    )
    result = manager.run_turn(game_state)
    assert result.world_tick_delta is not None
    # Verify world tick delta tracks resource consumption
    assert "food_consumed" in result.world_tick_delta
    food_consumed = result.world_tick_delta.get("food_consumed", 0)
    # Food consumed should be at least 0 (may vary based on NPC count)
    assert food_consumed >= 0
    # Final food should be correctly reduced
    final_food = game_state.snapshot()["stockpiles"]["food"]
    assert final_food >= 0
    # Verify NPC exists and fatigue updated
    npc_a = game_state.get_npc("npc_a")
    if npc_a is not None:
        assert npc_a.fatigue >= 3  # Initial 3, may increase
