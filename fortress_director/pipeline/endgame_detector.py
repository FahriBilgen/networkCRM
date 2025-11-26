"""Evaluates when the run should pivot into endgame mode."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.narrative.event_graph import EventNode


class EndgameDetector:
    """Collapse-aware detector that flags when the final act should begin."""

    def __init__(
        self,
        *,
        morale_threshold: int = 25,
        resource_threshold: int = 20,
        enemy_marker_threshold: int = 3,
    ) -> None:
        self._morale_threshold = morale_threshold
        self._resource_threshold = resource_threshold
        self._enemy_marker_threshold = enemy_marker_threshold

    def check(
        self,
        game_state: Any,
        threat_snapshot: ThreatSnapshot,
        *,
        event_node: EventNode | None = None,
    ) -> Dict[str, Any]:
        snapshot = self._coerce_snapshot(game_state)
        metrics = snapshot.get("metrics") or {}
        morale = self._coerce_int(metrics.get("morale"), 50)
        resources = self._coerce_int(metrics.get("resources"), 50)
        enemy_markers = self._count_enemy_markers(snapshot)
        final_trigger = False
        reason: str | None = None
        recommended = "strategic"
        if event_node is not None and event_node.is_final:
            return {
                "final_trigger": True,
                "reason": f"Reached final graph node: {event_node.id}",
                "recommended_path": self._recommended_from_tags(event_node.tags),
            }
        if threat_snapshot.phase == "collapse":
            if morale < self._morale_threshold:
                final_trigger = True
                reason = "low_morale"
                recommended = "desperate"
            elif resources < self._resource_threshold:
                final_trigger = True
                reason = "low_resources"
                recommended = "strategic"
            elif enemy_markers >= self._enemy_marker_threshold:
                final_trigger = True
                reason = "enemy_markers"
                recommended = "heroic"
        return {
            "final_trigger": final_trigger,
            "reason": reason,
            "recommended_path": recommended,
        }

    def _coerce_snapshot(self, game_state: Any) -> Dict[str, Any]:
        if hasattr(game_state, "snapshot"):
            return dict(game_state.snapshot())
        if isinstance(game_state, dict):
            return dict(game_state)
        raise TypeError("game_state must be a GameState or dict.")

    def _count_enemy_markers(self, snapshot: Mapping[str, Any]) -> int:
        markers = snapshot.get("map_event_markers")
        if not isinstance(markers, list):
            return 0
        total = 0
        for marker in markers:
            if not isinstance(marker, Mapping):
                continue
            entity = str(marker.get("entity_type") or "").lower()
            if "enemy" in entity or bool(marker.get("hostile")):
                total += 1
        return total

    @staticmethod
    def _coerce_int(value: Any, default: Any) -> int:
        if value is None:
            value = default
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default or 0)

    @staticmethod
    def _recommended_from_tags(tags: Sequence[str]) -> str:
        lowered = {str(tag).lower() for tag in tags if tag}
        if "collapse" in lowered:
            return "desperate"
        if "hope" in lowered:
            return "heroic"
        if "battle" in lowered:
            return "strategic"
        return "strategic"


__all__ = ["EndgameDetector"]
