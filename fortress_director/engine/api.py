"""Minimal engine API surface for host games."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import TurnResult, run_turn
from fortress_director.themes.loader import ThemeRegistry, load_builtin_themes
from fortress_director.themes.schema import ThemeConfig

DEFAULT_ENGINE_THEME = "siege_default"


class FortressDirectorEngine:
    """Convenience wrapper that exposes the director as an embeddable engine."""

    def __init__(
        self,
        theme_id: str = DEFAULT_ENGINE_THEME,
        *,
        registry: Optional[ThemeRegistry] = None,
    ) -> None:
        self._registry = registry or load_builtin_themes()
        self._theme = self._resolve_theme(theme_id)
        self._game_state = GameState.from_theme_config(self._theme)
        self._pending_external_events: List[Dict[str, Any]] = []
        self._last_ingested_events: List[Dict[str, Any]] = []

    @property
    def theme(self) -> ThemeConfig:
        return self._theme

    def reset(self, theme_id: Optional[str] = None) -> Dict[str, Any]:
        """Reset internal state, optionally switching to a different theme."""

        if theme_id and theme_id != self._theme.id:
            self._theme = self._resolve_theme(theme_id)
        self._game_state = GameState.from_theme_config(self._theme)
        self._pending_external_events.clear()
        self._last_ingested_events.clear()
        return self.get_state_snapshot()

    def get_state_snapshot(self) -> Dict[str, Any]:
        """
        Return a compact view of the current GameState for host consumers.

        The snapshot is intentionally simplified so that embedding games do not need
        to understand every internal field from GameState.
        """

        snapshot = self._game_state.snapshot()
        domain = self._game_state.as_domain()
        return {
            "turn": snapshot.get("turn"),
            "turn_limit": snapshot.get("turn_limit"),
            "game_over": self._game_state.game_over,
            "ending_id": self._game_state.ending_id,
            "theme": {
                "id": self._theme.id,
                "label": self._theme.label,
                "description": self._theme.description,
            },
            "map": snapshot.get("map", {}),
            "metrics": snapshot.get("metrics", {}),
            "npc_positions": domain.npc_positions(),
            "structures": domain.structure_integrities(),
            "markers": domain.event_list(),
            "external_events": list(snapshot.get("external_events") or []),
        }

    def inject_external_event(self, event: Dict[str, Any]) -> None:
        """Queue an external event (battle_started, gate_opened, etc.)."""

        if not isinstance(event, dict):
            raise ValueError("event must be a dictionary payload")
        payload = dict(event)
        payload.setdefault("id", f"ext_{uuid4().hex}")
        payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        payload.setdefault("source", "external")
        self._pending_external_events.append(payload)
        self._append_external_event_to_state(payload)

    def run_turn(self, player_choice: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a simulated turn and return a delta for the host."""

        ingested_events = self._ingest_external_events()
        result = run_turn(
            self._game_state,
            player_choice=player_choice,
            player_action_context=None,
            theme=self._theme,
        )
        domain = self._game_state.as_domain()
        delta = {
            "narrative": result.narrative,
            "turn": result.turn_number,
            "theme_id": self._theme.id,
            "game_over": self._game_state.game_over,
            "ending_id": self._game_state.ending_id,
            "npc_positions": domain.npc_positions(),
            "structures": domain.structure_integrities(),
            "markers": domain.event_list(),
            "atmosphere": result.atmosphere or {},
            "state_delta": result.state_delta,
            "suggested_events_for_host": self._build_host_events(result),
            "ingested_external_events": ingested_events,
            "player_options": result.player_options,
            "executed_actions": result.executed_actions,
            "event_node": {
                "id": result.event_node_id,
                "description": result.event_node_description,
                "is_final": result.event_node_is_final,
            },
        }
        if result.final_payload:
            delta["final_payload"] = result.final_payload
        if result.world_tick_delta:
            delta["world_tick_delta"] = result.world_tick_delta
        return delta

    def _resolve_theme(self, theme_id: str) -> ThemeConfig:
        try:
            return self._registry.get(theme_id)
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Unknown theme '{theme_id}'.") from exc

    def _ingest_external_events(self) -> List[Dict[str, Any]]:
        if not self._pending_external_events:
            self._last_ingested_events = []
            return []
        snapshot = self._game_state.snapshot()
        log_entries = list(snapshot.get("log") or [])
        consumed: List[Dict[str, Any]] = []
        for event in self._pending_external_events:
            consumed.append(event)
            label = event.get("label") or event.get("type") or event.get("id")
            if label:
                log_entries.append(f"[external] {label}")
        self._game_state.apply_delta(
            {
                "log": log_entries[-50:],
            }
        )
        self._pending_external_events.clear()
        self._last_ingested_events = consumed
        return consumed

    def _append_external_event_to_state(self, event: Dict[str, Any]) -> None:
        snapshot = self._game_state.snapshot()
        history = list(snapshot.get("external_events") or [])
        history.append(event)
        self._game_state.apply_delta({"external_events": history[-25:]})

    def _build_host_events(self, result: TurnResult) -> List[Dict[str, Any]]:
        if not result.ui_events:
            return []
        formatted: List[Dict[str, Any]] = []
        for entry in result.ui_events:
            if isinstance(entry, dict):
                formatted.append(entry)
            else:
                formatted.append({"message": str(entry)})
        return formatted


__all__ = ["FortressDirectorEngine"]
