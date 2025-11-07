"""State service helpers extracted from the monolithic orchestrator module."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)


class StateServices:
    """Utility helpers that operate on world-state dictionaries."""

    def accumulate_emotional_memory(
        self, state: Dict[str, Any], character_output: List[Dict[str, Any]]
    ) -> None:
        """Persist NPC emotional echoes to keep short-term memory consistent."""

        try:
            if not isinstance(state, dict):
                return
            emotions = state.setdefault("emotional_memory", [])
            turn_value = state.get("turn") or state.get("current_turn", 0)
            for entry in character_output or []:
                if not isinstance(entry, dict):
                    continue
                speech = str(entry.get("speech", "")).strip()
                if not speech:
                    continue
                emotions.append(
                    {
                        "turn": turn_value,
                        "name": entry.get("name", "Unknown"),
                        "intent": entry.get("intent"),
                        "speech": speech,
                    }
                )
            if len(emotions) > 40:
                del emotions[:-40]
        except Exception:
            LOGGER.debug("Failed to accumulate emotional memory.", exc_info=True)

    def record_npc_journal(
        self, state: Dict[str, Any], character_output: List[Dict[str, Any]]
    ) -> None:
        """Append short NPC journal snippets for the turn."""

        if not isinstance(state, dict):
            return
        journal = state.setdefault("npc_journal", [])
        turn_value = int(state.get("turn") or state.get("current_turn") or 0)
        for entry in character_output or []:
            if not isinstance(entry, dict):
                continue
            speech = str(entry.get("speech") or entry.get("action") or "").strip()
            if not speech:
                continue
            journal.append(
                {
                    "turn": turn_value,
                    "name": entry.get("name"),
                    "intent": entry.get("intent"),
                    "entry": speech,
                }
            )
        if len(journal) > 24:
            del journal[:-24]

    def collect_active_flags(self, state: Dict[str, Any], limit: int = 8) -> List[str]:
        raw_flags = state.get("flags")
        if not isinstance(raw_flags, list):
            return []
        cleaned: List[str] = []
        for flag in raw_flags:
            if isinstance(flag, str):
                trimmed = flag.strip()
                if trimmed:
                    cleaned.append(trimmed)
        return cleaned[:limit]

    def build_npc_trust_overview(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        overview: List[Dict[str, Any]] = []
        npc_trust = state.get("npc_trust")
        if not isinstance(npc_trust, dict):
            return overview
        items = sorted(
            npc_trust.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        for name, score in items[:5]:
            overview.append({"name": str(name), "trust": float(score or 0)})
        return overview

    def collect_npc_journal_recent(
        self, state: Dict[str, Any], limit: int = 5
    ) -> List[Dict[str, Any]]:
        journal = state.get("npc_journal")
        if not isinstance(journal, list):
            return []
        recent = journal[-limit:]
        sanitized: List[Dict[str, Any]] = []
        for entry in recent:
            if not isinstance(entry, dict):
                continue
            sanitized.append(
                {
                    "turn": int(entry.get("turn", 0) or 0),
                    "name": entry.get("name"),
                    "intent": entry.get("intent"),
                    "entry": entry.get("entry"),
                }
            )
        return sanitized

    def build_metrics_panel(
        self, state: Dict[str, Any], result: Dict[str, Any]
    ) -> Dict[str, float]:
        metrics_panel: Dict[str, float] = {}
        snapshot = result.get("metrics_after") or state.get("metrics") or {}
        if not isinstance(snapshot, dict):
            return metrics_panel
        allowed_keys = {
            "order",
            "morale",
            "resources",
            "knowledge",
            "corruption",
            "glitch",
        }
        for key, value in snapshot.items():
            if key not in allowed_keys:
                continue
            try:
                metrics_panel[key] = float(value)
            except (TypeError, ValueError):
                continue
        return metrics_panel

    def build_map_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        map_state: Dict[str, Any] = {
            "current_room": state.get("current_room"),
            "day": state.get("day"),
            "time": state.get("time"),
        }
        map_state["npc_positions"] = self.normalize_npc_locations(state)
        structures_raw = state.get("structures")
        structures: List[Dict[str, Any]] = []
        iterator: Optional[List[Any]] = None

        if isinstance(structures_raw, dict):
            iterator = list(structures_raw.items())
        elif isinstance(structures_raw, list):
            iterator = [
                (entry.get("id"), entry)
                for entry in structures_raw
                if isinstance(entry, dict)
            ]
        else:
            iterator = []

        for struct_id, payload in iterator:
            if not isinstance(payload, dict):
                continue
            structures.append(
                {
                    "id": str(struct_id),
                    "status": payload.get("status"),
                    "durability": payload.get("durability"),
                    "max_durability": payload.get("max_durability"),
                }
            )
        map_state["structures"] = structures
        return map_state

    def normalize_npc_locations(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        positions: List[Dict[str, Any]] = []
        raw_locations = state.get("npc_locations")
        if isinstance(raw_locations, dict):
            iterator = raw_locations.items()
        elif isinstance(raw_locations, list):
            iterator = []
            for entry in raw_locations:
                if isinstance(entry, dict):
                    iterator.append(
                        (
                            entry.get("id")
                            or entry.get("npc_id")
                            or entry.get("name"),
                            entry.get("room") or entry.get("location"),
                        )
                    )
        else:
            iterator = []
        for npc_id, room in iterator:
            positions.append(
                {
                    "id": str(npc_id) if npc_id is not None else None,
                    "room": room,
                }
            )
        return positions
