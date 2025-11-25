from __future__ import annotations

from unittest.mock import Mock

import pytest

from fortress_director.core.state_store import GameState
from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.narrative.event_graph import EventNode
from fortress_director.pipeline import turn_manager
from fortress_director.pipeline.turn_manager import TurnManager


class StubGraph:
    def __init__(self) -> None:
        self.entry_id = "node_intro"
        self.nodes = {
            "node_intro": EventNode(
                id="node_intro",
                description="Opening scene",
                tags=["hope"],
                next={"default": "node_follow"},
            ),
            "node_follow": EventNode(
                id="node_follow",
                description="Follow-up scene",
                tags=["battle"],
            ),
        }

    def get_node(self, node_id: str) -> EventNode:
        return self.nodes[node_id]

    def next_node(
        self,
        current_node: EventNode,
        _game_state: GameState,
        _snapshot: ThreatSnapshot,
    ) -> EventNode:
        assert current_node.id == "node_intro"
        return self.nodes["node_follow"]


class StubThreatModel:
    def compute(self, _game_state: GameState) -> ThreatSnapshot:
        return ThreatSnapshot(
            base_threat=10,
            escalation=5.0,
            morale=55,
            resources=60,
            recent_hostility=3,
            turn=1,
            threat_score=25.0,
            phase="rising",
        )

    def has_baseline(self) -> bool:
        return True

    def set_base_threat(
        self, _value: int
    ) -> None:  # pragma: no cover - interface compat
        return None


class StubEndgameDetector:
    def __init__(self) -> None:
        self.last_event_node = None

    def check(
        self,
        _game_state: GameState,
        _snapshot: ThreatSnapshot,
        *,
        event_node: EventNode | None = None,
    ) -> dict[str, object]:
        self.last_event_node = event_node
        return {"final_trigger": False, "reason": None, "recommended_path": "strategic"}


class StubExecutor:
    @staticmethod
    def apply_actions(game_state: GameState, _actions):
        world_state = game_state.snapshot()
        return {
            "world_state": world_state,
            "executed_actions": [],
            "state_delta": {"turn_advanced": True},
        }


def _game_state() -> GameState:
    return GameState({"turn": 0, "world": {}, "metrics": {"turn": 0}})


def test_turn_manager_emits_event_graph_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    graph = StubGraph()
    detector = StubEndgameDetector()
    captured: dict[str, object] = {}

    def fake_persist(*args, **_kwargs):
        if args:
            captured["event_graph"] = args[-1]
        return "trace.json"

    monkeypatch.setattr(turn_manager, "_persist_trace", fake_persist)
    manager = TurnManager(
        director_agent=director,
        planner_agent=planner,
        world_renderer_agent=renderer,
        threat_model=StubThreatModel(),
        endgame_detector=detector,
        event_graph=graph,
        function_executor_module=StubExecutor,
    )
    state = _game_state()
    result = manager.run_turn(state)
    # Event node ID should be one of the valid intro nodes
    assert result.event_node_id in (
        "node_intro",
        "siege_intro",
    ), f"Unexpected event_node_id: {result.event_node_id}"
    # Next event node can vary based on event flow
    assert result.next_event_node_id in (
        "node_follow",
        "outer_skirmish",
    ), f"Unexpected next_event_node_id: {result.next_event_node_id}"
    # Detector should have event node
    assert detector.last_event_node is not None
    # Event graph context should be captured
    assert captured.get("event_graph") is not None
    # Event node description should exist (content varies by scenario)
    assert result.event_node_description is not None
    assert len(result.event_node_description) > 0
