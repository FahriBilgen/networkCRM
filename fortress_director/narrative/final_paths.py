"""Deterministic branching logic for the final narrative routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping

FINAL_PATH_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "victory_defense": {
        "type": "object",
        "required": ["fortress_status", "honors", "rebuild_plan"],
        "properties": {
            "fortress_status": {"type": "string"},
            "honors": {"type": "array", "items": {"type": "string"}},
            "rebuild_plan": {"type": "string"},
        },
    },
    "evacuation_success": {
        "type": "object",
        "required": ["convoy_manifest", "escort_status"],
        "properties": {
            "convoy_manifest": {"type": "array", "items": {"type": "string"}},
            "escort_status": {"type": "string"},
            "after_action_notes": {"type": "string"},
        },
    },
    "heroic_last_stand": {
        "type": "object",
        "required": ["fallen_heroes", "final_hold_points"],
        "properties": {
            "fallen_heroes": {"type": "array", "items": {"type": "string"}},
            "final_hold_points": {"type": "array", "items": {"type": "string"}},
            "legacy_quote": {"type": "string"},
        },
    },
    "collapse_failure": {
        "type": "object",
        "required": ["breach_vectors", "civilian_losses"],
        "properties": {
            "breach_vectors": {"type": "array", "items": {"type": "string"}},
            "civilian_losses": {"type": "integer"},
            "retribution_plan": {"type": "string"},
        },
    },
    "unknown_anomaly": {
        "type": "object",
        "required": ["phenomena", "containment_status"],
        "properties": {
            "phenomena": {"type": "array", "items": {"type": "string"}},
            "containment_status": {"type": "string"},
            "anomaly_vector": {"type": "string"},
        },
    },
    "betrayal_ending": {
        "type": "object",
        "required": ["traitor_profile", "power_shift"],
        "properties": {
            "traitor_profile": {"type": "string"},
            "power_shift": {"type": "string"},
            "reprisal_plan": {"type": "string"},
        },
    },
    "bittersweet_survival": {
        "type": "object",
        "required": ["casualty_report", "remaining_supplies"],
        "properties": {
            "casualty_report": {"type": "string"},
            "remaining_supplies": {"type": "integer"},
            "next_objective": {"type": "string"},
        },
    },
    "evacuation_failure": {
        "type": "object",
        "required": ["breakdown_point", "survivor_count"],
        "properties": {
            "breakdown_point": {"type": "string"},
            "survivor_count": {"type": "integer"},
        },
    },
    "npc_takeover": {
        "type": "object",
        "required": ["faction", "demands"],
        "properties": {
            "faction": {"type": "string"},
            "demands": {"type": "array", "items": {"type": "string"}},
        },
    },
    "leadership_collapse": {
        "type": "object",
        "required": ["mutiny_log", "vacuum_risk"],
        "properties": {
            "mutiny_log": {"type": "string"},
            "vacuum_risk": {"type": "string"},
        },
    },
}

FINAL_PATH_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "victory_defense": {
        "title": "Victory Through Vigilance",
        "tone": "triumphant",
        "summary": "The defenders hold every wall and force the siege to break.",
    },
    "evacuation_success": {
        "title": "Convoy in the Storm",
        "tone": "hopeful",
        "summary": "Civilians slip away under heavy escort while commanders stay behind.",
    },
    "heroic_last_stand": {
        "title": "The Final Rampart",
        "tone": "defiant",
        "summary": "Leaders spend their lives to buy one last dawn for the fortress.",
    },
    "collapse_failure": {
        "title": "Citadel Consumed",
        "tone": "tragic",
        "summary": "Threat overwhelms morale, and the inner walls fold inward.",
    },
    "unknown_anomaly": {
        "title": "Anomaly Ascendant",
        "tone": "eerie",
        "summary": "No strategy explains the outcome; reality itself fractures.",
    },
    "betrayal_ending": {
        "title": "Knives Behind the Banner",
        "tone": "ominous",
        "summary": "Leadership fractures inward; loyalties realign in shadow.",
    },
    "bittersweet_survival": {
        "title": "Ashen Dawn",
        "tone": "somber",
        "summary": "The fortress survives, but the cost scars every survivor.",
    },
    "evacuation_failure": {
        "title": "Convoy Lost",
        "tone": "mourning",
        "summary": "The escape collapsed before the gates fully opened.",
    },
    "npc_takeover": {
        "title": "New Regents Rise",
        "tone": "uneasy",
        "summary": "Factions inside the fortress redirect the campaign's future.",
    },
    "leadership_collapse": {
        "title": "Command Fractured",
        "tone": "bleak",
        "summary": "No single voice remains to rally the walls or civilians.",
    },
}


@dataclass(frozen=True)
class FinalPath:
    """Container describing a single ending branch."""

    id: str
    title: str
    tone: str
    summary: str
    schema: Dict[str, Any]

    def to_payload(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "tone": self.tone,
            "summary": self.summary,
            "schema": self.schema,
        }


def determine_final_path(
    snapshot: Mapping[str, Any],
    *,
    metrics: Mapping[str, Any] | None = None,
    threat_score: float | None = None,
) -> FinalPath:
    """Evaluate the snapshot against the authored decision graph."""

    metrics = metrics or {}
    morale = _coerce_int(metrics.get("morale"), default=50)
    threat_value = _resolve_threat(snapshot, metrics, threat_score)
    population_ratio = _population_alive_ratio(snapshot)
    key_losses = _count_key_npc_losses(snapshot)
    corruption = _coerce_int(metrics.get("corruption"), default=0)
    alignment = _resolve_alignment(snapshot, metrics)

    if morale > 60 and threat_value < 40:
        return _path("victory_defense")
    if morale > 40 and population_ratio > 0.7:
        return _path("evacuation_success")
    if threat_value > 80 and key_losses > 2:
        return _path("heroic_last_stand")
    if threat_value > 90 and morale < 30:
        return _path("collapse_failure")
    if corruption > 60:
        return _path("unknown_anomaly")
    if alignment < -20:
        return _path("betrayal_ending")
    return _path("bittersweet_survival")


def _path(path_id: str) -> FinalPath:
    definition = FINAL_PATH_DEFINITIONS.get(path_id, FINAL_PATH_DEFINITIONS["bittersweet_survival"])
    schema = FINAL_PATH_SCHEMAS.get(path_id, FINAL_PATH_SCHEMAS["bittersweet_survival"])
    return FinalPath(
        id=path_id,
        title=definition["title"],
        tone=definition["tone"],
        summary=definition["summary"],
        schema=schema,
    )


def _resolve_threat(
    snapshot: Mapping[str, Any],
    metrics: Mapping[str, Any],
    threat_score: float | None,
) -> float:
    if threat_score is not None:
        return float(threat_score)
    metric_value = metrics.get("threat")
    if metric_value is not None:
        return float(_coerce_int(metric_value))
    world = snapshot.get("world") or {}
    stability = world.get("stability")
    if stability is not None:
        # Higher stability lowers threat, so invert it.
        return max(0.0, 100.0 - float(_coerce_int(stability)))
    return 50.0


def _population_alive_ratio(snapshot: Mapping[str, Any]) -> float:
    locations = snapshot.get("npc_locations")
    if not isinstance(locations, list):
        return 1.0
    total = 0
    alive = 0
    for npc in locations:
        if not isinstance(npc, Mapping):
            continue
        total += 1
        status = str(npc.get("status") or npc.get("state") or "").lower()
        health = _coerce_int(npc.get("health"), default=100)
        if status in {"dead", "fallen"} or health <= 0:
            continue
        alive += 1
    if total == 0:
        return 1.0
    return alive / total


def _count_key_npc_losses(snapshot: Mapping[str, Any]) -> int:
    key_terms = {"captain", "commander", "leader", "warden", "seer", "strategist"}
    locations = snapshot.get("npc_locations")
    if not isinstance(locations, list):
        return 0
    losses = 0
    for npc in locations:
        if not isinstance(npc, Mapping):
            continue
        role = str(npc.get("role") or "").lower()
        if not any(term in role for term in key_terms):
            continue
        status = str(npc.get("status") or npc.get("state") or "").lower()
        health = _coerce_int(npc.get("health"), default=100)
        if status in {"dead", "fallen"} or health <= 0:
            losses += 1
    return losses


def _resolve_alignment(
    snapshot: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> int:
    scores = snapshot.get("scores") or {}
    if isinstance(scores, Mapping) and "leadership_alignment" in scores:
        return _coerce_int(scores.get("leadership_alignment"))
    if "leadership_alignment" in metrics:
        return _coerce_int(metrics.get("leadership_alignment"))
    logic_score = _coerce_int(scores.get("logic_score"), default=metrics.get("order", 50))
    emotion_score = _coerce_int(scores.get("emotion_score"), default=metrics.get("morale", 50))
    return logic_score - emotion_score


def _coerce_int(value: Any, *, default: Any = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(default)
        except (TypeError, ValueError):
            return 0


__all__ = ["FinalPath", "determine_final_path"]
