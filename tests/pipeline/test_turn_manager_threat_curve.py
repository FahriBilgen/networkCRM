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

    def set_base_threat(self, _value: int) -> None:  # pragma: no cover - interface compat
        return None


class StubEventCurve:
    def __init__(self, seed: str = "minor_scouting"):
        self._seed = seed

    def next_event(self, _snapshot: ThreatSnapshot, _game_state: GameState) -> str:
        return self._seed


class StubEndgameDetector:
    def __init__(self, final: bool = False):
        self._final = final

    def check(
        self,
        _game_state: GameState,
        _snapshot: ThreatSnapshot,
        *,
        event_node=None,
    ) -> dict[str, object]:
        return {
            "final_trigger": self._final,
            "reason": "low_morale" if self._final else None,
            "recommended_path": "desperate" if self._final else "strategic",
        }


class StubExecutor:
    @staticmethod
    def apply_actions(game_state: GameState, _actions):
        world_state = game_state.snapshot()
        return {
            "world_state": world_state,
            "executed_actions": [],
            "state_delta": {"turn_advanced": True},
        }


def _snapshot(phase: str = "rising") -> ThreatSnapshot:
    return ThreatSnapshot(
        base_threat=20,
        escalation=15.0,
        morale=45,
        resources=40,
        recent_hostility=4,
        turn=3,
        threat_score=42.0,
        phase=phase,
    )


def _game_state() -> GameState:
    return GameState({"turn": 0, "world": {}, "metrics": {"turn": 0}})


def test_turn_manager_threads_threat_context() -> None:
    snapshot = _snapshot()
    director = Mock()
    director.generate_intent.return_value = {
        "scene_intent": {"focus": "stabilize", "turn": 1},
        "player_options": [],
    }
    planner = Mock()
    planner.plan_actions.return_value = {"planned_actions": []}
    renderer = Mock()
    renderer.render.return_value = {
        "narrative_block": "story beat",
        "npc_dialogues": [],
        "atmosphere": {},
    }
    manager = TurnManager(
        director_agent=director,
        planner_agent=planner,
        world_renderer_agent=renderer,
        threat_model=StubThreatModel(snapshot),
        event_curve=StubEventCurve("supply_drop"),
        endgame_detector=StubEndgameDetector(False),
        function_executor_module=StubExecutor,
    )
    result = manager.run_turn(_game_state())
    _, kwargs = director.generate_intent.call_args
    assert kwargs["threat_snapshot"] == snapshot
    assert kwargs["event_seed"] == "supply_drop"
    assert kwargs["event_node"] is not None
    renderer.render.assert_called_once()
    render_kwargs = renderer.render.call_args.kwargs
    assert render_kwargs["threat_phase"] == snapshot.phase
    assert render_kwargs["event_seed"] == "supply_drop"
    assert render_kwargs["event_node"] == kwargs["event_node"]
    assert result.event_seed == "supply_drop"
    assert result.threat_snapshot == snapshot


def test_turn_manager_limits_planner_on_final_trigger() -> None:
    snapshot = _snapshot("collapse")
    director = Mock()
    director.generate_intent.return_value = {
        "scene_intent": {"focus": "stabilize", "turn": 1},
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
    manager = TurnManager(
        director_agent=director,
        planner_agent=planner,
        world_renderer_agent=renderer,
        threat_model=StubThreatModel(snapshot),
        event_curve=StubEventCurve("final_breach"),
        endgame_detector=StubEndgameDetector(True),
        function_executor_module=StubExecutor,
    )
    manager.run_turn(_game_state())
    assert planner.plan_actions.call_args.kwargs["max_calls"] == 2
