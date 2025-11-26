"""Graph-based narrative progression helpers."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


@dataclass
class EventNode:
    """Lightweight container that represents a beat on the event graph."""

    id: str
    description: str
    tags: List[str] = field(default_factory=list)
    next: Dict[str, str] = field(default_factory=dict)
    is_final: bool = False


class EventGraph:
    """Utility that advances between EventNodes using weighted transitions."""

    def __init__(self, nodes: Dict[str, EventNode], entry_id: str) -> None:
        if entry_id not in nodes:
            raise ValueError(f"Entry node '{entry_id}' missing from node map.")
        self.nodes = nodes
        self.entry_id = entry_id

    def get_node(self, node_id: str) -> EventNode:
        """Return the node by *node_id* or raise KeyError."""

        return self.nodes[node_id]

    def next_node(
        self,
        current_node: EventNode,
        game_state: Any,
        threat_snapshot: Any,
    ) -> EventNode:
        """
        Select the next EventNode based on coop metrics, threat signals,
        and deterministic weighted randomness.
        """

        if current_node.is_final:
            return current_node
        if not current_node.next:
            return current_node
        snapshot = self._coerce_snapshot(game_state)
        metrics = snapshot.get("metrics") or {}
        morale = self._to_int(metrics.get("morale"))
        resources = self._to_int(
            metrics.get("resources") or snapshot.get("world", {}).get("resources")
        )
        threat_phase = getattr(threat_snapshot, "phase", None)
        candidate_ids = list(dict.fromkeys(current_node.next.values()))
        candidate_nodes: List[EventNode] = []
        candidate_weights: List[float] = []
        for candidate_id in candidate_ids:
            node = self.nodes.get(candidate_id)
            if node is None:
                continue
            lowered_tags = self._lowered_tags(node)
            weight = self._base_weight(node.tags)
            if threat_phase == "collapse" and "collapse" in lowered_tags:
                weight += 2.5
            if morale < 25 and "despair" in lowered_tags:
                weight += 1.5
            if resources > 40 and "hope" in lowered_tags:
                weight += 1.5
            candidate_nodes.append(node)
            candidate_weights.append(max(0.1, weight))
        if not candidate_nodes:
            return current_node
        seed = self._build_seed(snapshot)
        return self._select_candidate(candidate_nodes, candidate_weights, seed)

    # Internal helpers -------------------------------------------------

    @staticmethod
    def _base_weight(tags: Sequence[str]) -> float:
        return 1.0 + (0.25 * len(tags))

    @staticmethod
    def _lowered_tags(node: EventNode) -> List[str]:
        return [tag.lower() for tag in node.tags]

    def _coerce_snapshot(self, game_state: Any) -> Dict[str, Any]:
        if hasattr(game_state, "snapshot"):
            snapshot = game_state.snapshot()
            if isinstance(snapshot, Mapping):
                return dict(snapshot)
        if isinstance(game_state, Mapping):
            return dict(game_state)
        raise TypeError("game_state must provide snapshot() or behave like a mapping.")

    def _build_seed(self, snapshot: Mapping[str, Any]) -> int:
        metrics = snapshot.get("metrics") or {}
        turn = self._to_int(snapshot.get("turn") or metrics.get("turn"))
        order = self._to_int(metrics.get("order"))
        return turn + order * 17

    def _select_candidate(
        self,
        candidates: Sequence[EventNode],
        weights: Sequence[float],
        seed: int,
    ) -> EventNode:
        rng = random.Random(seed)
        chosen = rng.choices(list(candidates), weights=list(weights), k=1)[0]
        return chosen

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


__all__ = ["EventNode", "EventGraph"]
