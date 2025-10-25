from __future__ import annotations

import hashlib
import logging

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

    def evaluate(self, variables: Dict[str, Any]) -> Dict[str, Any]:
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

        variables = dict(variables)
        variables["tolerance"] = self.tolerance
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
