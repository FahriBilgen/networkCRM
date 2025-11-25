from __future__ import annotations

from types import SimpleNamespace
from typing import Dict

from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.narrative.event_graph import EventGraph, EventNode


def test_next_node_deterministic():
    nodes = {
        "a": EventNode(id="a", description="a", next={"default": "b", "alt": "c"}),
        "b": EventNode(id="b", description="b"),
        "c": EventNode(id="c", description="c"),
    }
    g = EventGraph(nodes, entry_id="a")
    current = g.get_node("a")
    game_state = {"turn": 2, "metrics": {"order": 3, "morale": 50, "resources": 50}}
    threat = SimpleNamespace(phase="calm")
    n1 = g.next_node(current, game_state, threat)
    n2 = g.next_node(current, game_state, threat)
    assert n1.id == n2.id
    assert n1.id in {"b", "c"}


class InspectableGraph(EventGraph):
    def __init__(self, nodes: Dict[str, EventNode], entry_id: str) -> None:
        super().__init__(nodes, entry_id)
        self.last_weights: list[float] | None = None
        self.last_candidates: list[str] | None = None

    def _select_candidate(self, candidates, weights, seed):  # type: ignore[override]
        self.last_weights = list(weights)
        self.last_candidates = [node.id for node in candidates]
        max_index = self.last_weights.index(max(self.last_weights))
        return list(candidates)[max_index]


def _snapshot(phase: str = "rising") -> ThreatSnapshot:
    return ThreatSnapshot(
        base_threat=15,
        escalation=5.0,
        morale=45,
        resources=40,
        recent_hostility=2,
        turn=3,
        threat_score=30.0,
        phase=phase,
    )


def test_graph_returns_final_node_when_already_final() -> None:
    final_node = EventNode(id="node_final", description="Final", is_final=True)
    graph = EventGraph({"node_final": final_node}, entry_id="node_final")
    result = graph.next_node(final_node, {}, _snapshot())
    assert result is final_node


def test_graph_boosts_weighted_candidates() -> None:
    nodes = {
        "start": EventNode(
            id="start",
            description="Root",
            next={"default": "hopeful", "collapse": "doom"},
        ),
        "hopeful": EventNode(
            id="hopeful",
            description="Hope path",
            tags=["hope"],
        ),
        "doom": EventNode(
            id="doom",
            description="Collapse path",
            tags=["collapse"],
        ),
    }
    graph = InspectableGraph(nodes, entry_id="start")
    snapshot = _snapshot("collapse")
    game_state = {"turn": 8, "metrics": {"order": 4, "morale": 10, "resources": 65}}
    chosen = graph.next_node(nodes["start"], game_state, snapshot)
    assert graph.last_candidates == ["hopeful", "doom"]
    assert chosen.id == "doom"  # collapse tag boosted during collapse phase
    assert graph.last_weights and graph.last_weights[1] > graph.last_weights[0]


def test_graph_uses_deterministic_seed() -> None:
    nodes = {
        "start": EventNode(
            id="start",
            description="Root",
            next={"default": "alpha", "secondary": "beta"},
        ),
        "alpha": EventNode(id="alpha", description="A"),
        "beta": EventNode(id="beta", description="B"),
    }
    graph = EventGraph(nodes, entry_id="start")
    game_state = {"turn": 5, "metrics": {"order": 2, "morale": 55, "resources": 30}}
    snapshot = _snapshot("rising")
    first = graph.next_node(nodes["start"], game_state, snapshot)
    second = graph.next_node(nodes["start"], game_state, snapshot)
    assert first.id == second.id
