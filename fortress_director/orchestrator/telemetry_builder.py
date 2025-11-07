"""Telemetry and player-view assembly helpers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fortress_director.orchestrator.state_services import StateServices


class TelemetryBuilder:
    """Constructs telemetry payloads and compact UI views."""

    def __init__(self, state_services: StateServices) -> None:
        self._state_services = state_services

    def build_guardrail_notes(
        self, guardrail_stats: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        if not isinstance(guardrail_stats, dict):
            return []
        notes: List[Dict[str, str]] = []
        if guardrail_stats.get("planner_lowered_wall_integrity"):
            notes.append(
                {
                    "type": "planner_guardrail",
                    "message": "World agent wall damage skipped because planner already reduced integrity this turn.",
                }
            )
        skipped = guardrail_stats.get("world_wall_integrity_skipped", 0) or 0
        if skipped:
            notes.append(
                {
                    "type": "world_guardrail",
                    "message": f"Prevented {int(skipped)} duplicate wall integrity reductions.",
                }
            )
        for source in guardrail_stats.get("objective_urgency_skipped", []) or []:
            notes.append(
                {
                    "type": "objective_guardrail",
                    "message": f"Additional objective urgency adjustments from {source} were skipped.",
                }
            )
        for resource in guardrail_stats.get("stockpile_collapsed", []) or []:
            notes.append(
                {
                    "type": "stockpile_guardrail",
                    "message": f"Duplicate stockpile adjustments on '{resource}' collapsed into a single call.",
                }
            )
        return notes

    def build_player_view(
        self,
        state: Dict[str, Any],
        result: Dict[str, Any],
        *,
        guardrail_notes: Optional[List[Dict[str, str]]] = None,
        scene_text: Optional[str] = None,
        world_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compose the player_view blob using canonical state slices."""

        scene = (scene_text or result.get("scene", "")).strip()
        world_summary = (world_text or result.get("WORLD_CONTEXT", ""))[:400]

        raw_options = result.get("options") or []
        options: List[Dict[str, Any]] = []
        for opt in raw_options:
            if isinstance(opt, dict):
                options.append(
                    {"id": opt.get("id"), "text": str(opt.get("text", "")).strip()}
                )

        primary_reaction = ""
        reactions = result.get("character_reactions") or []
        if reactions and isinstance(reactions, list):
            first = reactions[0]
            if isinstance(first, dict):
                primary_reaction = str(
                    first.get("speech") or first.get("action") or ""
                ).strip()

        sfs = result.get("safe_function_results") or []
        sf_names = [
            sf.get("name") for sf in sfs if isinstance(sf, dict) and sf.get("name")
        ]

        metrics_panel = self._state_services.build_metrics_panel(state, result)
        map_state = self._state_services.build_map_state(state)
        safe_history = result.get("safe_function_history") or []
        guardrail_feed = guardrail_notes or result.get("guardrail_notes") or []

        player_view: Dict[str, Any] = {
            "short_scene": scene[:400],
            "short_world": world_summary,
            "options": options,
            "primary_reaction": primary_reaction,
            "safe_functions": sf_names,
            "metrics_panel": metrics_panel or None,
            "active_flags": self._state_services.collect_active_flags(state),
            "npc_trust_overview": self._state_services.build_npc_trust_overview(state),
            "npc_journal_recent": self._state_services.collect_npc_journal_recent(
                state
            ),
            "guardrail_notes": guardrail_feed,
            "map_state": map_state,
            "npc_locations": list(map_state.get("npc_positions", [])),
            "safe_function_history": safe_history,
            "fallback_strategy": result.get("fallback_strategy"),
            "fallback_summary": result.get("fallback_summary"),
        }
        if state.get("final_summary"):
            player_view["final_summary"] = state.get("final_summary")
        if result.get("judge_feedback"):
            player_view["judge_feedback"] = result.get("judge_feedback")
        return player_view
