from __future__ import annotations

"""Planner Agent that proposes a small, JSON-only function call plan.

The agent receives compact world context and a list of available safe
functions, and returns a minimal plan with a bounded number of calls.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient


class PlannerAgent(BaseAgent):
    """Produces a deterministic, validator-friendly execution plan."""

    def __init__(
        self,
        *,
        client: Optional[OllamaClient] = None,
        prompt_path: Optional[Path] = None,
    ) -> None:
        template_path = prompt_path or build_prompt_path("planner_prompt.txt")
        template = PromptTemplate(template_path)
        super().__init__(
            name="Planner",
            prompt_template=template,
            model_config=get_model_config("planner"),
            client=client or default_ollama_client("planner"),
        )

    def plan(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        result = self.run(variables=variables)
        return result if isinstance(result, dict) else {}
