from __future__ import annotations

import hashlib
import logging
import random

"""Judge Agent implementation providing lore consistency checks."""
from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    AgentOutputError,
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient
from fortress_director.settings import (
    JUDGE_BIAS_REWEIGHT,
    JUDGE_TONE_ALIGNMENT_THRESHOLD,
    JUDGE_BASE_VETO_PROB,
)


LOGGER = logging.getLogger(__name__)


class JudgeAgent(BaseAgent):
    LOGGER = LOGGER
    """Validates narrative content against established lore."""

    def __init__(
        self, *, client: Optional[OllamaClient] = None, tolerance: int = 0
    ) -> None:
        self.tolerance = tolerance
        self._content_hashes = set()  # For redundancy detection
        template = PromptTemplate(build_prompt_path("judge_prompt.txt"))
        super().__init__(
            name="Judge",
            prompt_template=template,
            model_config=get_model_config("judge"),
            client=client or default_ollama_client("judge"),
        )

    def evaluate(
        self, variables: Dict[str, Any], seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """Return lore consistency verdict for supplied content."""
        # Redundancy detection: hash the content
        content = variables.get("content", "")
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        if content_hash in self._content_hashes:
            LOGGER.info("Redundant content detected, skipping evaluation")
            return {"consistent": True, "reason": "redundant_content"}
        self._content_hashes.add(content_hash)
        # Keep only last 10 hashes
        if len(self._content_hashes) > 10:
            self._content_hashes.pop()

        # Read repetition-related signals (injected by orchestrator)
        repetition_count = int(variables.get("repetition_count", 0) or 0)
        atmosphere_repetition_count = int(
            variables.get("atmosphere_repetition_count", 0) or 0
        )
        motif_repetition = bool(variables.get("motif_repetition", False))
        creativity_flag = bool(variables.get("creativity", False))

        # Small probabilistic disagreement to force variation when
        # repetition is detected
        # Base disagreement probability; scaled by repetition signals. We
        # apply a bias reweight read from settings so we can tune how often
        # the Judge forces variation during testing.
        base_disagreement = JUDGE_BASE_VETO_PROB
        scale = 0.0 + (0.05 * repetition_count)
        scale += 0.03 * atmosphere_repetition_count
        if motif_repetition:
            scale += 0.03
        disagreement_prob = min(0.8, base_disagreement + scale)
        # Apply reweighting from settings: lowering JUDGE_BIAS_REWEIGHT
        # increases the disagreement probability (makes Judge less
        # approving). Reweight is expected in 0.0-1.0.
        try:
            reweight = float(JUDGE_BIAS_REWEIGHT)
        except Exception:
            reweight = 0.6
        # multiplier ranges roughly from 1.0..(1.0+(1-reweight))
        multiplier = 1.0 + max(0.0, (1.0 - reweight))
        disagreement_prob = min(0.95, disagreement_prob * multiplier)

        # If creative path is active, be slightly more permissive; otherwise
        # stricter
        if not creativity_flag and disagreement_prob > 0:
            roll = random.random()
            LOGGER.debug(
                "Judge stochastic disagreement roll=%.3f vs prob=%.3f (rep=%s,"
                " atmos=%s, motif=%s)",
                roll,
                disagreement_prob,
                repetition_count,
                atmosphere_repetition_count,
                motif_repetition,
            )
            if roll < disagreement_prob:
                # Return a small structured veto to force the creativity/event
                # loop to reframe
                verdict = {
                    "consistent": False,
                    "reason": "stochastic_repetition_veto",
                    "penalty_magnitude": {"morale": -1, "glitch": 1},
                    "coherence": 20,
                    "feedback": {"reframe_scene": True},
                }
                LOGGER.info("Judge forced disagreement due to repetition")
                LOGGER.debug("Judge forced verdict: %s", verdict)
                return verdict

        variables = dict(variables)
        variables["tolerance"] = self.tolerance
        if seed is not None:
            variables["seed"] = seed
        self.LOGGER.info("JudgeAgent.evaluate called with variables")
        try:
            result = self.run(variables=variables)
            self.LOGGER.debug("Model returned: %s", result)
            if not isinstance(result, dict):
                self.LOGGER.error(
                    "Judge agent must return a JSON object, got: %s", result
                )
                raise AgentOutputError("Judge agent must return a JSON object")
            self.LOGGER.info("Judge verdict: %s", result)
            # Enforce tone alignment threshold: if the model returns a
            # tone_alignment score below the configured threshold, treat
            # the content as inconsistent so downstream logic can reframe.
            try:
                tone_val = result.get("tone_alignment")
                if tone_val is not None:
                    tone_val = float(tone_val)
                else:
                    tone_val = None
            except Exception:
                tone_val = None
            if tone_val is not None and tone_val < JUDGE_TONE_ALIGNMENT_THRESHOLD:
                LOGGER.info(
                    "Judge rejecting content: tone_alignment %s < %s",
                    tone_val,
                    JUDGE_TONE_ALIGNMENT_THRESHOLD,
                )
                # Mark inconsistent and add a mild penalty to encourage
                # reframing by creativity or event agents.
                result["consistent"] = False
                result["reason"] = "tone_alignment_below_threshold"
                result["penalty_magnitude"] = {"morale": -1, "glitch": 1}
                result["coherence"] = min(result.get("coherence", 100), 30)
            return result
        except Exception as exc:
            self.LOGGER.error(
                "Exception in JudgeAgent.evaluate: %s", exc, exc_info=True
            )
            raise


def check_win_loss(
    metrics: Dict[str, Any],
    *,
    turn: int,
    turn_limit: int,
    triggered_loss: bool = False,
) -> Dict[str, str]:
    """Evaluate win/loss state using supplied metrics."""

    LOGGER.debug(
        "Evaluating win/loss (turn=%s/%s) with metrics=%s",
        turn,
        turn_limit,
        metrics,
    )

    def _as_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    order = _as_int(metrics.get("order"), 0)
    morale = _as_int(metrics.get("morale"), 0)
    resources = _as_int(metrics.get("resources"), 0)
    glitch = _as_int(metrics.get("glitch"), 0)
    corruption = _as_int(metrics.get("corruption"), 0)

    status = "ongoing"
    reason = "thresholds_not_met"

    # Check triggered_loss first - overrides all other conditions
    if triggered_loss:
        status = "loss"
        reason = "glitch_overload"
    elif order >= 70 and morale >= 70 and glitch <= 30:
        status = "win"
        reason = "fortress_stabilized"
    elif order <= 20:
        status = "loss"
        reason = "order_collapse"
    elif resources <= 0:
        status = "loss"
        reason = "resources_depleted"
    elif glitch >= 85:
        status = "loss"
        reason = "glitch_overload"
    # Multi-condition loss: High glitch + low morale + low resources
    elif glitch >= 60 and morale <= 30 and resources <= 20:
        status = "loss"
        reason = "multi_condition_crisis"
    # System collapse: High glitch with low morale or high corruption
    elif glitch > 30 and (morale < 30 or corruption > 80):
        status = "loss"
        reason = "system_collapse"
    elif turn >= max(1, turn_limit):
        status = "loss"
        reason = "turn_limit_reached"

    outcome = {"status": status, "reason": reason}
    LOGGER.info("Win/loss evaluation result: %s", outcome)
    return outcome
