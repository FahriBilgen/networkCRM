from __future__ import annotations

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


class JudgeAgent(BaseAgent):
    LOGGER = logging.getLogger(__name__)
    """Validates narrative content against established lore."""

    def __init__(
        self, *, client: Optional[OllamaClient] = None, tolerance: int = 0
    ) -> None:
        self.tolerance = tolerance
        template = PromptTemplate(build_prompt_path("judge_prompt.txt"))
        super().__init__(
            name="Judge",
            prompt_template=template,
            model_config=get_model_config("judge"),
            client=client or default_ollama_client(),
        )

    def evaluate(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Return lore consistency verdict for supplied content. Logs every step."""
        variables = dict(variables)
        variables["tolerance"] = self.tolerance
        self.LOGGER.info("JudgeAgent.evaluate called with variables: %s", variables)
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
