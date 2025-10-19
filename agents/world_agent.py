from __future__ import annotations
import logging

"""Implementation of the World Agent using the Ollama client stack."""
from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient


class WorldAgent(BaseAgent):
    LOGGER = logging.getLogger(__name__)
    """Describes the atmosphere and sensory texture of the environment."""

    def __init__(self, *, client: Optional[OllamaClient] = None) -> None:
        template = PromptTemplate(build_prompt_path("world_prompt.txt"))
        super().__init__(
            name="World",
            prompt_template=template,
            model_config=get_model_config("world"),
            client=client or default_ollama_client(),
        )

    def describe(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Produce atmospheric context for the current turn. Logs every step."""
        self.LOGGER.info("WorldAgent.describe called with variables: %s", variables)
        try:
            result = self.run(variables=variables)
            self.LOGGER.debug("Model returned: %s", result)
            if not isinstance(result, dict):
                self.LOGGER.error(
                    "World agent must return a JSON object, got: %s", result
                )
                raise ValueError("World agent must return a JSON object")
            self.LOGGER.info("World description: %s", result)
            return result
        except Exception as exc:
            self.LOGGER.error(
                "Exception in WorldAgent.describe: %s", exc, exc_info=True
            )
            raise
