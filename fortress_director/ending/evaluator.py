from __future__ import annotations

from typing import Any, Dict

from fortress_director.core.state_store import GameState
from fortress_director.themes.schema import ThemeConfig, ThemeEndingSpec

FALLBACK_ENDING_ID = "fallback_default"


def evaluate_ending(state: GameState, theme: ThemeConfig) -> str:
    """
    Returns ending_id (from theme.endings) based on theme-specific conditions.
    """

    if theme is None:
        return FALLBACK_ENDING_ID
    snapshot = state.snapshot()
    for ending in theme.endings:
        if _meets_conditions(snapshot, theme, ending):
            return ending.id
    return FALLBACK_ENDING_ID


def _meets_conditions(
    snapshot: Dict[str, Any],
    theme: ThemeConfig,
    ending: ThemeEndingSpec,
) -> bool:
    conditions = ending.conditions or {}
    metrics = snapshot.get("metrics") or {}
    if "wall_integrity_min" in conditions:
        if _metric_value(metrics, "wall_integrity") < float(conditions["wall_integrity_min"]):
            return False
    if "morale_min" in conditions:
        if _metric_value(metrics, "morale") < float(conditions["morale_min"]):
            return False
    if "threat_max" in conditions:
        if _metric_value(metrics, "threat") > float(conditions["threat_max"]):
            return False
    if "resources_min" in conditions:
        if _metric_value(metrics, "resources") < float(conditions["resources_min"]):
            return False
    if "npc_survival_min_ratio" in conditions:
        if _npc_survival_ratio(snapshot, theme) < float(conditions["npc_survival_min_ratio"]):
            return False
    if "structure_integrity_min_ratio" in conditions:
        if (
            _structure_integrity_ratio(snapshot)
            < float(conditions["structure_integrity_min_ratio"])
        ):
            return False
    return True


def _metric_value(metrics: Dict[str, Any], key: str) -> float:
    try:
        return float(metrics.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _npc_survival_ratio(snapshot: Dict[str, Any], theme: ThemeConfig) -> float:
    baseline = max(1, len(theme.npcs))
    living = 0
    for npc in snapshot.get("npc_locations", []):
        if isinstance(npc, dict) and not npc.get("hostile", False):
            living += 1
    return living / baseline if baseline else 1.0


def _structure_integrity_ratio(snapshot: Dict[str, Any]) -> float:
    structures = snapshot.get("structures")
    if not isinstance(structures, dict) or not structures:
        return 1.0
    ratios = []
    for payload in structures.values():
        if not isinstance(payload, dict):
            continue
        current = payload.get("integrity", payload.get("durability"))
        maximum = payload.get("max_integrity", payload.get("max_durability", 100))
        try:
            current_val = float(current or 0)
            max_val = float(maximum or 0)
        except (TypeError, ValueError):
            continue
        if max_val <= 0:
            continue
        ratios.append(max(0.0, min(1.0, current_val / max_val)))
    if not ratios:
        return 1.0
    return sum(ratios) / len(ratios)


__all__ = ["evaluate_ending", "FALLBACK_ENDING_ID"]
