"""Deterministic escalation-aware event seed selection."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Sequence

from fortress_director.core.threat_model import ThreatSnapshot

DEFAULT_PHASE_EVENTS: Dict[str, Sequence[str]] = {
    "calm": ("minor_scouting", "supply_drop", "weather_shift"),
    "rising": ("sabotage", "scouting_party", "reinforcement_arrival"),
    "peak": ("enemy_assault", "fire_breakout", "breach_warning"),
    "collapse": ("final_breach", "last_reserve", "evacuation_crisis"),
}


class EventCurve:
    """Independent pacing system that emits turn-based thematic event seeds."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        phase_overrides = self.config.get("phase_events") or {}
        self._phase_events: Dict[str, Sequence[str]] = {}
        for phase, defaults in DEFAULT_PHASE_EVENTS.items():
            override = phase_overrides.get(phase)
            if isinstance(override, Sequence) and override:
                self._phase_events[phase] = tuple(str(item) for item in override)
            else:
                self._phase_events[phase] = defaults

    def next_event(
        self,
        threat_snapshot: ThreatSnapshot,
        game_state: Any,
    ) -> str:
        """
        Returns a deterministic event seed based on the threat curve and state.

        calm     -> low-intensity events (minor scouting, weather shifts)
        rising   -> scouting parties and sabotage
        peak     -> direct assaults and spreading fires
        collapse -> breaches and final stand cues
        """

        if threat_snapshot is None:
            raise ValueError("threat_snapshot is required")
        phase = threat_snapshot.phase or "calm"
        events = self._phase_events.get(phase, self._phase_events["calm"])
        cursor = self._calculate_cursor(threat_snapshot, game_state)
        index = cursor % len(events)
        return str(events[index])

    # Internal helpers -------------------------------------------------

    def _calculate_cursor(
        self,
        threat_snapshot: ThreatSnapshot,
        game_state: Any,
    ) -> int:
        snapshot = self._coerce_snapshot(game_state)
        metrics = snapshot.get("metrics") or {}
        morale = self._coerce_int(metrics.get("morale"), 60)
        resources = self._coerce_int(
            metrics.get("resources"), snapshot.get("world", {}).get("resources", 50)
        )
        enemy_pressure = self._count_enemy_markers(snapshot)
        turn = int(snapshot.get("turn") or threat_snapshot.turn or 0)
        base = int(round(threat_snapshot.threat_score))
        hostility = int(threat_snapshot.recent_hostility)
        resource_gap = max(0, 50 - resources)
        morale_gap = max(0, 80 - morale)
        momentum = (
            base
            + hostility * 3
            + morale_gap
            + resource_gap * 2
            + enemy_pressure * 5
            + turn
        )
        return max(0, momentum)

    def _coerce_snapshot(self, game_state: Any) -> Dict[str, Any]:
        if hasattr(game_state, "snapshot"):
            return dict(game_state.snapshot())
        if isinstance(game_state, dict):
            return dict(game_state)
        raise TypeError("game_state must be a GameState or dict.")

    def _count_enemy_markers(self, snapshot: Mapping[str, Any]) -> int:
        markers = snapshot.get("map_event_markers")
        if not isinstance(markers, Iterable):
            return 0
        total = 0
        for marker in markers:
            if not isinstance(marker, Mapping):
                continue
            entity_type = str(marker.get("entity_type") or "").lower()
            if "enemy" in entity_type or bool(marker.get("hostile")):
                total += 1
        return total

    @staticmethod
    def _coerce_int(value: Any, default: Any = 0) -> int:
        if value is None:
            value = default
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default or 0)


__all__ = ["EventCurve"]
