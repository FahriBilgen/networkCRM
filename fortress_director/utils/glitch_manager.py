"""Deterministic glitch propagation utilities for Fortress Director."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List

from fortress_director.utils.metrics_manager import MetricManager


@dataclass
class GlitchManager:
    """Compute glitch rolls and apply deterministic side-effects."""

    seed: int = 0

    def resolve_turn(
        self,
        *,
        metrics: MetricManager,
        turn: int,
    ) -> Dict[str, object]:
        current_glitch = metrics.value("glitch")
        roll = self._deterministic_roll(turn=turn, glitch=current_glitch)
        effects: List[str] = []
        triggered_loss = False

        if roll <= 30:
            effects.append("Minor static ripples along the parapets.")
            metrics.adjust_metric("glitch", 1, cause="glitch:cosmetic_noise")
        elif roll <= 60:
            effects.append("Pathfinding errors unsettle the patrol routes.")
            metrics.apply_bulk(
                (
                    ("order", -3, "glitch:medium_anomaly"),
                    ("morale", -2, "glitch:medium_anomaly"),
                    ("glitch", 4, "glitch:medium_anomaly"),
                )
            )
        elif roll < 85:
            effects.append("Major anomaly distorts the western wall segment.")
            metrics.apply_bulk(
                (
                    ("resources", -6, "glitch:major_anomaly"),
                    ("knowledge", -5, "glitch:major_anomaly"),
                    ("glitch", 6, "glitch:major_anomaly"),
                )
            )
        else:
            effects.append("Glitch cascade overwhelms containment protocols.")
            metrics.adjust_metric("glitch", 15, cause="glitch:overload")
            triggered_loss = True

        return {
            "roll": roll,
            "effects": effects,
            "triggered_loss": triggered_loss,
        }

    def _deterministic_roll(self, *, turn: int, glitch: int) -> int:
        payload = f"{self.seed}:{turn}:{glitch}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest[:4], "big") % 101
