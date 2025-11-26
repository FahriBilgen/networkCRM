"""Final narrative engine used when the campaign reaches its final turn."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from fortress_director.agents.world_renderer_agent import WorldRendererAgent
from fortress_director.core.function_registry import get_safe_function, load_defaults
from fortress_director.core.state_store import GameState
from fortress_director.core.threat_model import ThreatSnapshot
from fortress_director.narrative.final_paths import FinalPath, determine_final_path

Action = Dict[str, Any]
ActionResult = Dict[str, Any]
FinalNarrative = Dict[str, Any]


class FinalEngine:
    """Orchestrates the branching finale, action pack, and narrative output."""

    def __init__(
        self,
        *,
        world_renderer_agent: WorldRendererAgent | None = None,
    ) -> None:
        self._world_renderer = world_renderer_agent or WorldRendererAgent(use_llm=False)
        load_defaults()

    def run(
        self,
        game_state: GameState,
        *,
        threat_snapshot: ThreatSnapshot | None = None,
    ) -> Dict[str, Any]:
        snapshot = game_state.snapshot()
        metrics = snapshot.get("metrics") or {}
        event_history = _coerce_event_history(snapshot)
        final_path = self.determine_final_path(
            snapshot,
            event_history,
            threat_snapshot,
            metrics,
        )
        planned_actions = self.build_final_actions(final_path, snapshot)
        executed_actions = self._execute_final_actions(game_state, planned_actions)
        updated_snapshot = game_state.snapshot()
        metrics = updated_snapshot.get("metrics") or metrics
        npc_outcomes = self._build_npc_outcomes(updated_snapshot)
        structure_outcomes = self._build_structure_outcomes(updated_snapshot)
        resource_summary = self._build_resource_summary(updated_snapshot)
        threat_summary = self._build_threat_summary(threat_snapshot)
        world_context = {
            "metrics": metrics,
            "event_history": event_history[-8:],
            "threat": threat_summary,
            "npc_outcomes": npc_outcomes,
            "structure_outcomes": structure_outcomes,
            "resource_summary": resource_summary,
            "actions": executed_actions,
        }
        final_narrative = self.build_final_narrative(
            final_path,
            updated_snapshot,
            world_context,
        )
        return {
            "final_path": final_path.to_payload(),
            "npc_outcomes": npc_outcomes,
            "structure_outcomes": structure_outcomes,
            "resource_summary": resource_summary,
            "threat_summary": threat_summary,
            "final_actions": executed_actions,
            "final_narrative": final_narrative,
        }

    def determine_final_path(
        self,
        state: Mapping[str, Any],
        event_history: List[Mapping[str, Any]],
        threat: ThreatSnapshot | None,
        metrics: Mapping[str, Any],
    ) -> FinalPath:
        threat_value = getattr(threat, "threat_score", None)
        return determine_final_path(state, metrics=metrics, threat_score=threat_value)

    def build_final_actions(self, final_path: FinalPath, state: Mapping[str, Any]) -> List[Action]:
        """Return a deterministic safe-function action set for the finale."""

        structure_id = _primary_structure_id(state)
        npc_id = _primary_npc_id(state)
        coords = _primary_coordinates(state)
        base_actions = {
            "victory_defense": [
                {"function": "boost_allied_morale", "args": {"delta": 12}},
                {"function": "spawn_smoke_effect", "args": coords},
                {"function": "npc_final_move", "args": {"npc_id": npc_id, **coords}},
            ],
            "evacuation_success": [
                {"function": "trigger_mass_evacuate", "args": {}},
                {"function": "boost_allied_morale", "args": {"delta": 8}},
                {"function": "spawn_smoke_effect", "args": coords},
            ],
            "heroic_last_stand": [
                {"function": "ignite_structure", "args": {"structure_id": structure_id}},
                {"function": "spawn_mass_enemy_wave", "args": {"direction": "north", "strength": 90}},
                {"function": "npc_final_move", "args": {"npc_id": npc_id, "x": coords["x"], "y": coords["y"]}},
            ],
            "collapse_failure": [
                {"function": "collapse_structure", "args": {"structure_id": structure_id}},
                {"function": "spawn_fire_effect", "args": coords},
                {"function": "global_blackout", "args": {}},
            ],
            "unknown_anomaly": [
                {"function": "freeze_weather", "args": {"duration": 6}},
                {"function": "spawn_mass_enemy_wave", "args": {"direction": "void", "strength": 75}},
                {"function": "global_blackout", "args": {}},
            ],
            "betrayal_ending": [
                {"function": "spawn_mass_enemy_wave", "args": {"direction": "inner", "strength": 60}},
                {"function": "ignite_structure", "args": {"structure_id": structure_id}},
                {"function": "npc_final_move", "args": {"npc_id": npc_id, **coords}},
            ],
            "bittersweet_survival": [
                {"function": "trigger_mass_evacuate", "args": {}},
                {"function": "spawn_smoke_effect", "args": coords},
                {"function": "boost_allied_morale", "args": {"delta": 4}},
            ],
        }
        return base_actions.get(final_path.id, base_actions["bittersweet_survival"])

    def build_final_narrative(
        self,
        final_path: FinalPath,
        state: Mapping[str, Any],
        world_context: Mapping[str, Any],
    ) -> FinalNarrative:
        context = {
            "final_path": final_path.to_payload(),
            "state": state,
            "world_context": dict(world_context),
        }
        try:
            return self._world_renderer.render_final(context)
        except Exception:
            # Deterministic fallback
            paragraphs = [
                final_path.summary,
                "Civilians recount the final two turns as myth already hardening into legend.",
                "The fortress stands poised for whatever story follows.",
            ]
            return {
                "title": final_path.title,
                "tone": final_path.tone,
                "paragraphs": paragraphs,
                "atmosphere": {
                    "mood": final_path.tone,
                    "visuals": "Ash and embers weave through the skyline.",
                    "audio": "Distant horns echo beneath a low, resonant hum.",
                },
            }

    def _execute_final_actions(
        self,
        game_state: GameState,
        actions: Iterable[Action],
    ) -> List[ActionResult]:
        results: List[ActionResult] = []
        for index, action in enumerate(actions or []):
            name = str(action.get("function"))
            args = dict(action.get("args") or {})
            meta = get_safe_function(name)
            if meta is None or meta.handler is None:
                results.append(
                    {
                        "function": name,
                        "args": args,
                        "status": "error",
                        "log": f"Final action {name} is unavailable.",
                        "metrics": {},
                        "effects": {},
                    }
                )
                continue
            try:
                payload = meta.handler(game_state, **args)
            except Exception as exc:  # pragma: no cover - defensive
                payload = {
                    "status": "error",
                    "log": f"{name} failed: {exc}",
                }
            results.append(
                {
                    "function": name,
                    "args": args,
                    "status": payload.get("status", "applied"),
                    "log": payload.get("log", f"{name} executed."),
                    "metrics": payload.get("metrics", {}),
                    "effects": payload.get("effects", {}),
                }
            )
        return results

    def _build_npc_outcomes(self, snapshot: Mapping[str, Any]) -> List[Dict[str, Any]]:
        outcomes: List[Dict[str, Any]] = []
        for npc in snapshot.get("npc_locations", []) or []:
            if not isinstance(npc, Mapping):
                continue
            name = npc.get("name") or npc.get("id")
            status = str(npc.get("status") or "").lower()
            health = _safe_int(npc.get("health"), default=100)
            if status in {"dead", "fallen"} or health <= 0:
                fate = "fallen"
                color = "gray"
            elif "escaped" in status or npc.get("room") == "tunnels":
                fate = "escaped"
                color = "blue"
            else:
                fate = "alive"
                color = "green"
            outcomes.append(
                {
                    "id": npc.get("id"),
                    "name": name,
                    "fate": fate,
                    "color": color,
                }
            )
        return outcomes

    def _build_structure_outcomes(self, snapshot: Mapping[str, Any]) -> List[Dict[str, Any]]:
        structures = snapshot.get("structures") or {}
        if isinstance(structures, list):
            iterator = structures
        else:
            iterator = structures.values()
        outcomes: List[Dict[str, Any]] = []
        for struct in iterator:
            if not isinstance(struct, Mapping):
                continue
            outcomes.append(
                {
                    "id": struct.get("id"),
                    "status": struct.get("status", "unknown"),
                    "integrity": _safe_int(struct.get("integrity"), default=0),
                }
            )
        return outcomes

    def _build_resource_summary(self, snapshot: Mapping[str, Any]) -> Dict[str, Any]:
        metrics = snapshot.get("metrics") or {}
        stockpiles = snapshot.get("stockpiles") or {}
        return {
            "morale": _safe_int(metrics.get("morale"), default=50),
            "resources": _safe_int(metrics.get("resources"), default=40),
            "stockpiles": {
                "food": _safe_int(stockpiles.get("food"), default=0),
                "wood": _safe_int(stockpiles.get("wood"), default=0),
                "ore": _safe_int(stockpiles.get("ore"), default=0),
            },
        }

    def _build_threat_summary(
        self,
        threat_snapshot: ThreatSnapshot | None,
    ) -> Dict[str, Any]:
        if threat_snapshot is None:
            return {"phase": "unknown", "score": None}
        return {"phase": threat_snapshot.phase, "score": threat_snapshot.threat_score}


def _coerce_event_history(snapshot: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    timeline = snapshot.get("timeline")
    if isinstance(timeline, list):
        return [entry for entry in timeline if isinstance(entry, Mapping)]
    log_events = snapshot.get("log") or []
    return [{"text": item} for item in log_events if isinstance(item, str)]


def _primary_structure_id(state: Mapping[str, Any]) -> str:
    structures = state.get("structures") or {}
    if isinstance(structures, list) and structures:
        struct = structures[0]
        if isinstance(struct, Mapping) and struct.get("id"):
            return str(struct["id"])
    if isinstance(structures, Mapping):
        for key, value in structures.items():
            candidate = value.get("id") if isinstance(value, Mapping) else key
            if candidate:
                return str(candidate)
    return "inner_gate"


def _primary_npc_id(state: Mapping[str, Any]) -> str:
    npcs = state.get("npc_locations") or []
    if isinstance(npcs, list):
        for npc in npcs:
            if isinstance(npc, Mapping) and npc.get("id"):
                return str(npc["id"])
    return "rhea"


def _primary_coordinates(state: Mapping[str, Any]) -> Dict[str, int]:
    player = state.get("player_position") or {}
    x = _safe_int(player.get("x"), default=5)
    y = _safe_int(player.get("y"), default=5)
    return {"x": x, "y": y}


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


__all__ = ["FinalEngine"]
