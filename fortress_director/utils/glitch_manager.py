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

        # Trend-based loss trigger disabled for MVP testing
        if roll <= 30:
            effects.append("Minor static ripples along the parapets.")
            metrics.adjust_metric("glitch", 1, cause="glitch:cosmetic_noise")
            metrics.adjust_metric("morale", -1, cause="glitch:unease")
        elif roll <= 60:
            effects.append("Pathfinding errors unsettle the patrol routes.")
            metrics.apply_bulk(
                (
                    ("order", -2, "glitch:medium_anomaly"),
                    ("morale", -1, "glitch:medium_anomaly"),
                    ("glitch", 2, "glitch:medium_anomaly"),
                )
            )
        elif roll < 95:
            effects.append("Major anomaly distorts the western wall segment.")
            metrics.apply_bulk(
                (
                    ("resources", -3, "glitch:major_anomaly"),
                    ("knowledge", -2, "glitch:major_anomaly"),
                    ("glitch", 3, "glitch:major_anomaly"),
                )
            )
        elif roll < 99:
            effects.append("Glitch cascade partially contained.")
            metrics.adjust_metric("glitch", 3, cause="glitch:overload")
            # No loss for 95-98 rolls to reduce early-game false positives
        else:
            effects.append("Glitch cascade overwhelms containment protocols.")
            metrics.adjust_metric("glitch", 4, cause="glitch:overload")
            # Minimum 10 turn before loss can be triggered
            if turn >= 10:
                triggered_loss = True

        # Tie glitch to major events deterministically: if a major event flag is set
        # this turn, swing glitch by +/-5 based on roll parity to create drama.
        snapshot = metrics.snapshot()
        try:
            if bool(snapshot.get("major_flag_set")):
                if roll % 2 == 0:
                    metrics.adjust_metric("glitch", 5, cause="glitch:major_event_surge")
                    effects.append("Major event destabilizes the weave (glitch surges).")
                else:
                    metrics.adjust_metric("glitch", -5, cause="glitch:major_event_relief")
                    effects.append("Aftershock settles briefly (glitch subsides).")
        except Exception:
            pass

        # Rare catastrophic failure chance scaled by current glitch level
        # Deterministic via roll bands: when glitch >= 70 and roll in {7,57,77}
        try:
            if metrics.value("glitch") >= 70 and roll in (7, 57, 77):
                effects.append("Containment breach! Systems falter under extreme stress.")
                metrics.adjust_metric("order", -5, cause="glitch:breach")
                metrics.adjust_metric("morale", -5, cause="glitch:breach")
                triggered_loss = True
        except Exception:
            pass

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
