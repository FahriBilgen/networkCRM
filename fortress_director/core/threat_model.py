"""Threat curve computation and threat snapshots."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence

from fortress_director.core.function_registry import (
    FUNCTION_REGISTRY,
    load_defaults,
)

DEFAULT_WEIGHTS = {
    "base": 0.45,
    "escalation": 0.75,
    "morale_gap": 0.6,
    "resource_gap": 0.5,
    "hostility": 1.2,
}
DEFAULT_THRESHOLDS = {
    "calm": 20,
    "rising": 40,
    "peak": 65,
}
DEFAULT_ESCALATION = {
    "rate": 1.4,
    "curve": 1.1,
    "cap": 75,
}
DEFAULT_HOSTILITY = {
    "window": 4,
    "base": 4.0,
    "decay": 0.8,
    "keywords": (
        "attack",
        "assault",
        "breach",
        "fire",
        "enemy",
        "charge",
        "raider",
        "sabotage",
    ),
}


@dataclass
class ThreatSnapshot:
    base_threat: int
    escalation: float
    morale: int
    resources: int
    recent_hostility: int
    turn: int
    threat_score: float
    phase: str  # "calm", "rising", "peak", "collapse"


class ThreatModel:
    """Lightweight threat governor that merges metrics and pacing curves."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.cfg = config or {}
        self._weights = {
            "base": float(self._weights_cfg().get("base", DEFAULT_WEIGHTS["base"])),
            "escalation": float(
                self._weights_cfg().get("escalation", DEFAULT_WEIGHTS["escalation"])
            ),
            "morale_gap": float(
                self._weights_cfg().get("morale_gap", DEFAULT_WEIGHTS["morale_gap"])
            ),
            "resource_gap": float(
                self._weights_cfg().get("resource_gap", DEFAULT_WEIGHTS["resource_gap"])
            ),
            "hostility": float(
                self._weights_cfg().get("hostility", DEFAULT_WEIGHTS["hostility"])
            ),
        }
        thresholds = self.cfg.get("thresholds") or {}
        self._thresholds = {
            "calm": float(thresholds.get("calm", DEFAULT_THRESHOLDS["calm"])),
            "rising": float(thresholds.get("rising", DEFAULT_THRESHOLDS["rising"])),
            "peak": float(thresholds.get("peak", DEFAULT_THRESHOLDS["peak"])),
        }
        self._escalation_cfg = {**DEFAULT_ESCALATION, **(self.cfg.get("escalation") or {})}
        self._hostility_cfg = {**DEFAULT_HOSTILITY, **(self.cfg.get("hostility") or {})}
        self._base_threat = self.cfg.get("base_threat")
        load_defaults()
        self._combat_functions = {
            name
            for name, meta in FUNCTION_REGISTRY.items()
            if getattr(meta, "category", "").lower() == "combat"
        }

    def set_base_threat(self, value: int) -> None:
        """Explicitly set the base threat derived from an external spec."""

        self._base_threat = int(value)
        self.cfg["base_threat"] = self._base_threat

    def has_baseline(self) -> bool:
        """Return True if a base threat value has been locked."""

        return self._base_threat is not None

    def compute(self, game_state: Any) -> ThreatSnapshot:
        """
        Calculates the turn-by-turn threat curve using weighted metrics,
        recent actions, NPC losses, and global pacing.
        """

        snapshot = self._coerce_snapshot(game_state)
        metrics = snapshot.get("metrics") or {}
        base_threat = self._resolve_base_threat(snapshot)
        turn = int(snapshot.get("turn") or metrics.get("turn") or 0)
        escalation = self._compute_escalation(turn)
        morale = self._coerce_int(metrics.get("morale"), default=60)
        resources = self._coerce_int(
            metrics.get("resources"), default=snapshot.get("world", {}).get("resources")
        )
        recent_hostility = self._compute_recent_hostility(snapshot)
        morale_gap = 100 - morale
        resource_gap = 50 - resources
        threat_score = (
            base_threat * self._weights["base"]
            + escalation * self._weights["escalation"]
            + morale_gap * self._weights["morale_gap"]
            + resource_gap * self._weights["resource_gap"]
            + recent_hostility * self._weights["hostility"]
        )
        threat_score = max(0.0, round(min(threat_score, 100.0), 2))
        phase = self._determine_phase(threat_score)
        return ThreatSnapshot(
            base_threat=int(base_threat),
            escalation=float(round(escalation, 2)),
            morale=morale,
            resources=resources,
            recent_hostility=int(recent_hostility),
            turn=turn,
            threat_score=threat_score,
            phase=phase,
        )

    # Internal helpers -------------------------------------------------

    def _weights_cfg(self) -> Mapping[str, Any]:
        weights = self.cfg.get("weights")
        if isinstance(weights, Mapping):
            return weights
        return {}

    def _coerce_snapshot(self, game_state: Any) -> Dict[str, Any]:
        if hasattr(game_state, "snapshot"):
            return dict(game_state.snapshot())
        if isinstance(game_state, dict):
            return dict(game_state)
        raise TypeError("game_state must be a GameState or dict.")

    def _resolve_base_threat(self, snapshot: Mapping[str, Any]) -> int:
        if self._base_threat is None:
            metrics = snapshot.get("metrics") or {}
            fallback = metrics.get("threat") or snapshot.get("threat")
            self._base_threat = int(fallback or 0)
            self.cfg["base_threat"] = self._base_threat
        return int(self._base_threat)

    def _compute_escalation(self, turn: int) -> float:
        if turn <= 0:
            return 0.0
        rate = float(self._escalation_cfg.get("rate", DEFAULT_ESCALATION["rate"]))
        curve = float(self._escalation_cfg.get("curve", DEFAULT_ESCALATION["curve"]))
        cap = float(self._escalation_cfg.get("cap", DEFAULT_ESCALATION["cap"]))
        softened = math.pow(max(turn, 1), curve) * rate
        return min(cap, softened)

    def _compute_recent_hostility(self, snapshot: Mapping[str, Any]) -> int:
        history = snapshot.get("safe_function_history")
        entries: Sequence[Any]
        if isinstance(history, Sequence) and not isinstance(history, (str, bytes)):
            entries = history[-int(self._hostility_cfg.get("window", 4)) :]
        else:
            entries = []
        hostility = 0.0
        for idx, entry in enumerate(reversed(entries)):
            if self._entry_is_combat(entry):
                hostility += self._hostility_score(idx)
        if hostility:
            return int(round(hostility))
        # Fallback: inspect recent textual events for aggression hints.
        recent_events = snapshot.get("recent_events") or snapshot.get("log") or []
        keywords: Iterable[str] = self._hostility_cfg.get("keywords") or ()
        for idx, value in enumerate(reversed(list(recent_events)[-3:])):
            if not isinstance(value, str):
                continue
            lowered = value.lower()
            if any(keyword in lowered for keyword in keywords):
                hostility += self._hostility_score(idx) * 0.5
        combat_metrics = snapshot.get("metrics", {}).get("combat")
        if isinstance(combat_metrics, Mapping):
            total_skirmishes = self._coerce_int(combat_metrics.get("total_skirmishes"))
            if total_skirmishes:
                hostility += min(total_skirmishes, 5) * 0.5
            last_casualties = self._coerce_int(
                combat_metrics.get("last_casualties_friendly")
            ) + self._coerce_int(combat_metrics.get("last_casualties_enemy"))
            if last_casualties:
                hostility += min(last_casualties, 10) * 0.3
        return int(round(hostility))

    def _entry_is_combat(self, entry: Any) -> bool:
        if isinstance(entry, Mapping):
            name = str(entry.get("name") or entry.get("function") or "").lower()
            category = str(entry.get("category") or "").lower()
            metadata = entry.get("metadata") or {}
            metadata_category = ""
            if isinstance(metadata, Mapping):
                metadata_category = str(metadata.get("category") or "").lower()
            if name in self._combat_functions:
                return True
            if category == "combat" or metadata_category == "combat":
                return True
            if any(token in name for token in ("attack", "assault", "breach")):
                return True
        elif isinstance(entry, str):
            lowered = entry.lower()
            if any(keyword in lowered for keyword in self._hostility_cfg.get("keywords", ())):
                return True
        return False

    def _hostility_score(self, idx: int) -> float:
        base = float(self._hostility_cfg.get("base", DEFAULT_HOSTILITY["base"]))
        decay = float(self._hostility_cfg.get("decay", DEFAULT_HOSTILITY["decay"]))
        return max(0.0, base - idx * decay)

    def _determine_phase(self, score: float) -> str:
        if score < self._thresholds["calm"]:
            return "calm"
        if score < self._thresholds["rising"]:
            return "rising"
        if score < self._thresholds["peak"]:
            return "peak"
        return "collapse"

    @staticmethod
    def _coerce_int(value: Any, default: Any = 0) -> int:
        if value is None:
            value = default
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default or 0)


__all__ = ["ThreatModel", "ThreatSnapshot"]
