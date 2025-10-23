from __future__ import annotations

import logging

"""Implementation of the Event Agent that talks to a local Ollama model."""
from typing import Any, Dict, Optional

from fortress_director.agents.base_agent import (
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient


class EventAgent(BaseAgent):
    LOGGER = logging.getLogger(__name__)
    """Creates short narrative scenes and diegetic player options."""

    def __init__(self, *, client: Optional[OllamaClient] = None) -> None:
        template = PromptTemplate(build_prompt_path("event_prompt.txt"))
        super().__init__(
            name="Event",
            prompt_template=template,
            model_config=get_model_config("event"),
            client=client or default_ollama_client(),
        )

    def generate(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a turn event using the provided template variables. Logs every step."""
        self.LOGGER.info("EventAgent.generate called with variables: %s", variables)
        try:
            output = self.run(variables=variables)
            self.LOGGER.debug("Model returned: %s", output)
            if not isinstance(output, dict):
                self.LOGGER.error(
                    "Event agent must return a JSON object, got: %s", output
                )
                raise ValueError("Event agent must return a JSON object")
            norm = self._normalise_event(output)
            self.LOGGER.info("Normalized event output: %s", norm)
            return norm
        except Exception as exc:
            self.LOGGER.error(
                "Exception in EventAgent.generate: %s", exc, exc_info=True
            )
            raise

    def _normalise_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        scene = payload.get("scene")
        if not isinstance(scene, str):
            payload["scene"] = str(scene) if scene is not None else ""

        options = payload.get("options")
        if not isinstance(options, list):
            options = [] if options is None else [options]
        normalised_options = []
        for raw in options:
            if not isinstance(raw, dict):
                continue
            option = dict(raw)
            option_id = option.get("id")
            option_text = option.get("text")
            action_type = option.get("action_type")
            if not isinstance(option_id, str) or not option_id.strip():
                option_id = f"opt_{len(normalised_options) + 1}"
            if not isinstance(option_text, str) or not option_text.strip():
                option_text = "Unclear option"
            if not isinstance(action_type, str) or not action_type.strip():
                action_type = "talk"
            option["id"] = option_id.strip()
            option["text"] = option_text.strip()
            option["action_type"] = action_type.strip()
            normalised_options.append(option)
        if not normalised_options:
            normalised_options.append(
                {
                    "id": "opt_1",
                    "text": "Observe the situation from the wall.",
                    "action_type": "explore",
                }
            )
        payload["options"] = normalised_options

        major_event = payload.get("major_event")
        payload["major_event"] = True if major_event is True else False

        return payload
