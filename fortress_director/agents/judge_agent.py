from __future__ import annotations

import hashlib
import json
import logging
import random
from pathlib import Path

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
    JUDGE_SOFT_MAX_CORRECTION_PER_TURN,
    JUDGE_PERSIST_WINDOW,
)


LOGGER = logging.getLogger(__name__)

COHERENCE_THRESHOLD = 75.0
INTEGRITY_THRESHOLD = 75.0


class JudgeAgent(BaseAgent):
    LOGGER = LOGGER
    """Validates narrative content against established lore."""

    def __init__(
        self,
        *,
        client: Optional[OllamaClient] = None,
        tolerance: int = 0,
        prompt_path: Optional[Path] = None,
    ) -> None:
        self.tolerance = tolerance
        self._content_hashes = set()  # For redundancy detection
        template_path = prompt_path or build_prompt_path("judge_prompt.txt")
        template = PromptTemplate(template_path)
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

        # Run deterministic heuristics first so offline tests have stable outcomes.
        heuristic_verdict = self._evaluate_heuristics(variables)
        if heuristic_verdict is not None:
            LOGGER.info("Judge heuristic verdict applied: %s", heuristic_verdict)
            return heuristic_verdict

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
                verdict = {
                    "consistent": False,
                    "reason": "stochastic_repetition_veto",
                    "penalty": "mild",
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
            penalty_applied = "none"

            # Coherence and integrity thresholds to keep narrative grounded.
            def _as_float(value: Any) -> Optional[float]:
                try:
                    return float(value)
                except Exception:
                    return None

            coherence_val = _as_float(result.get("coherence"))
            if coherence_val is not None and coherence_val < COHERENCE_THRESHOLD:
                LOGGER.info(
                    "Judge rejecting content: coherence %.1f < %.1f",
                    coherence_val,
                    COHERENCE_THRESHOLD,
                )
                result["consistent"] = False
                result["reason"] = "coherence below threshold"
                result["penalty_magnitude"] = result.get("penalty_magnitude", {"morale": -1, "glitch": 1})
                penalty_applied = "minor_penalty"

            integrity_val = _as_float(result.get("integrity"))
            if integrity_val is not None and integrity_val < INTEGRITY_THRESHOLD:
                LOGGER.info(
                    "Judge rejecting content: integrity %.1f < %.1f",
                    integrity_val,
                    INTEGRITY_THRESHOLD,
                )
                result["consistent"] = False
                result["reason"] = "integrity below threshold"
                result.setdefault("penalty_magnitude", {"morale": -1, "glitch": 1})
                penalty_applied = "minor_penalty"

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
            if (
                tone_val is not None
                and tone_val < JUDGE_TONE_ALIGNMENT_THRESHOLD
                and result.get("consistent", True)
            ):
                LOGGER.info(
                    "Judge rejecting content: tone_alignment %s < %s",
                    tone_val,
                    JUDGE_TONE_ALIGNMENT_THRESHOLD,
                )
                # Mark inconsistent and add a mild penalty to encourage
                # reframing by creativity or event agents.
                result["consistent"] = False
                result["reason"] = "tone_alignment below threshold"
                result["penalty_magnitude"] = {"morale": -1, "glitch": 1}
                result["coherence"] = min(result.get("coherence", 100), 30)
                penalty_applied = "minor_penalty"
            # Always surface a soft-edit policy so the orchestrator can respect
            # anomaly persistence and cap normalization speed.
            try:
                soft_policy = result.setdefault("soft_edit_policy", {})
                if not isinstance(soft_policy, dict):
                    soft_policy = {}
                    result["soft_edit_policy"] = soft_policy
            except Exception:
                soft_policy = {"max_correction_per_turn": JUDGE_SOFT_MAX_CORRECTION_PER_TURN,
                               "persist_window": JUDGE_PERSIST_WINDOW}
                result["soft_edit_policy"] = soft_policy
            soft_policy.setdefault("max_correction_per_turn", JUDGE_SOFT_MAX_CORRECTION_PER_TURN)
            soft_policy.setdefault("persist_window", JUDGE_PERSIST_WINDOW)
            # Back-compat for tests expecting 'penalty_applied'
            if "penalty_applied" not in result:
                result["penalty_applied"] = penalty_applied
            return result
        except Exception as exc:
            self.LOGGER.error(
                "Exception in JudgeAgent.evaluate: %s", exc, exc_info=True
            )
            raise

    def _evaluate_heuristics(self, variables: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Lightweight checks that catch obvious inconsistencies without LLM calls."""

        world_context = str(variables.get("WORLD_CONTEXT", "") or "")
        content_raw = variables.get("content", "") or ""
        try:
            content_json = json.loads(content_raw)
            if not isinstance(content_json, dict):
                content_json = {}
        except Exception:
            content_json = {}
        scene_text = str(content_json.get("scene", "") or "")
        choice_text = str(
            (content_json.get("player_choice") or {}).get("text", "") or ""
        )
        full_text = f"{scene_text} {choice_text}".lower()

        # Heuristic 1: Impossible physical action (flying without plausible support).
        flight_keywords = ("fly", "levitat", "soar", "hover")
        support_keywords = (
            "wing",
            "magic",
            "spell",
            "dragon",
            "glider",
            "jet",
            "wind",
            "rope",
            "ladder",
            "bridge",
        )
        has_flight = any(kw in full_text for kw in flight_keywords)
        has_invisible_wings = "invisible wing" in full_text
        has_support = any(sk in full_text for sk in support_keywords)
        if has_flight and (has_invisible_wings or not has_support):
            return {
                "consistent": False,
                "reason": "Impossible physical action detected: flight without support",
                "penalty": "medium",
                "penalty_magnitude": {"morale": -2, "glitch": 2},
            }

        # Heuristic 2: Character trait violation (betrayal vs loyalty).
        if "loyal" in world_context.lower():
            betrayal_keywords = ("betray", "traitor", "defect", "sell out")
            if any(kw in full_text for kw in betrayal_keywords):
                return {
                    "consistent": False,
                    "reason": "Character loyalty conflict: betrayal contradicts established traits",
                    "penalty": "mild",
                    "penalty_magnitude": {"morale": -1, "glitch": 1},
                }

        # Heuristic 3: Repetition detection using repetition_count or memory layers.
        repetition_count = int(variables.get("repetition_count", 0) or 0)
        if repetition_count >= 3:
            return {
                "consistent": True,
                "reason": "Repetition detected in recent memory layers",
                "penalty": "mild",
                "penalty_magnitude": {"morale": -1, "glitch": 1},
                "feedback": {"reframe_scene": True},
            }

        memory_layers = variables.get("memory_layers")
        if isinstance(memory_layers, list) and scene_text:
            recent_matches = [
                layer for layer in memory_layers if isinstance(layer, str) and scene_text in layer
            ]
            if len(recent_matches) >= 3:
                return {
                    "consistent": True,
                    "reason": "Repetition detected in recent memory layers",
                    "penalty": "mild",
                    "penalty_magnitude": {"morale": -1, "glitch": 1},
                    "feedback": {"reframe_scene": True},
                }

        return None


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

