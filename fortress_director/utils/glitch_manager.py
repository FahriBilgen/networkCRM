"""Deterministic glitch propagation utilities for Fortress Director."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Dict, List

from fortress_director.utils.metrics_manager import MetricManager

LOGGER = logging.getLogger(__name__)


@dataclass
class GlitchManager:
    """Compute glitch rolls and apply deterministic side-effects."""

    seed: int = 0
    previous_glitch: int = 0

    def resolve_turn(
        self,
        *,
        metrics: MetricManager,
        turn: int,
        finalized: bool = False,
    ) -> Dict[str, object]:
        if finalized:
            LOGGER.info("Game finalized, skipping glitch resolution")
            return {"roll": 0, "effects": [], "triggered_loss": False}
        current_glitch = metrics.value("glitch")
        LOGGER.info(
            "Resolving glitch (turn=%s, seed=%s, current_glitch=%s)",
            turn,
            self.seed,
            current_glitch,
        )
        LOGGER.debug("Metrics before glitch resolution: %s", metrics.snapshot())
        roll = self._deterministic_roll(turn=turn, glitch=current_glitch)
        effects: List[str] = []
        triggered_loss = False

        # Trend-based loss trigger: if glitch > 25 and increase > 10, trigger loss
        glitch_increase = current_glitch - self.previous_glitch
        if current_glitch > 25 and glitch_increase > 10:
            effects.append("Glitch momentum overload triggers early cascade.")
            metrics.adjust_metric("glitch", 10, cause="glitch:momentum_overload")
            triggered_loss = True
        elif roll <= 30:
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

        # Update previous glitch for next turn
        self.previous_glitch = metrics.value("glitch")

        LOGGER.info(
            "Glitch roll complete: roll=%s, triggered_loss=%s",
            roll,
            triggered_loss,
        )
        LOGGER.debug("Metrics after glitch resolution: %s", metrics.snapshot())
        LOGGER.debug("Glitch effects applied: %s", effects)

        return {
            "roll": roll,
            "effects": effects,
            "triggered_loss": triggered_loss,
        }

    def _deterministic_roll(self, *, turn: int, glitch: int) -> int:
        payload = f"{self.seed}:{turn}:{glitch}".encode("utf-8")
        digest = hashlib.sha256(payload).digest()
        return int.from_bytes(digest[:4], "big") % 101
