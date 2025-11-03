from __future__ import annotations

"""Director Agent responsible for pacing and turn-level directives."""

from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient


class DirectorAgent(BaseAgent):
    """Generates pacing and strategic directives for the turn."""

    def __init__(self, *, client: Optional[OllamaClient] = None) -> None:
        template = PromptTemplate(build_prompt_path("director_prompt.txt"))
        super().__init__(
            name="Director",
            prompt_template=template,
            model_config=get_model_config("director"),
            client=client or default_ollama_client("director"),
        )

    def evaluate(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        result = self.run(variables=variables)
        return result if isinstance(result, dict) else {}
