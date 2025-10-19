from __future__ import annotations
import logging

"""Implementation of the Character Agent for NPC reactions."""
from typing import Any, Dict, List, Optional

from fortress_director.agents.base_agent import (
    AgentOutputError,
    BaseAgent,
    PromptTemplate,
    build_prompt_path,
    default_ollama_client,
    get_model_config,
)
from fortress_director.llm.ollama_client import OllamaClient


MAX_SPEECH_LENGTH = 360


class CharacterAgent(BaseAgent):
    LOGGER = logging.getLogger(__name__)
    """Produces NPC intents, actions, dialogue, and mechanical effects."""

    def __init__(self, *, client: Optional[OllamaClient] = None) -> None:
        template = PromptTemplate(build_prompt_path("character_prompt.txt"))
        super().__init__(
            name="Character",
            prompt_template=template,
            model_config=get_model_config("character"),
            client=client or default_ollama_client(),
        )

    def react(self, variables: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate structured NPC reactions for the current turn. Logs every step."""
        self.LOGGER.info("CharacterAgent.react called with variables: %s", variables)
        try:
            result = self.run(variables=variables)
            self.LOGGER.debug("Model returned: %s", result)
            if isinstance(result, list):
                out = self._normalise_entries(result)
                self.LOGGER.info("Normalized output (list): %s", out)
                return out
            if isinstance(result, dict):
                # Some models respond with a single character object instead of
                # the expected list; wrap it for downstream consumers.
                if {"name", "intent", "action"}.issubset(result.keys()):
                    out = self._normalise_entries([result])
                    self.LOGGER.info("Normalized output (dict): %s", out)
                    return out
                for key in ("characters", "npcs", "responses"):
                    candidates = result.get(key)
                    if isinstance(candidates, list):
                        out = self._normalise_entries(candidates)
                        self.LOGGER.info("Normalized output (candidates): %s", out)
                        return out
            snippet = str(result)[:200]
            self.LOGGER.error("Agent output error: %s", snippet)
            raise AgentOutputError(
                "Character agent must return a JSON list; received: " + snippet
            )
        except Exception as exc:
            self.LOGGER.error(
                "Exception in CharacterAgent.react: %s", exc, exc_info=True
            )
            raise
            # Some models respond with a single character object instead of
            # the expected list; wrap it for downstream consumers.
            if {"name", "intent", "action"}.issubset(result.keys()):
                return self._normalise_entries([result])
            for key in ("characters", "npcs", "responses"):
                candidates = result.get(key)
                if isinstance(candidates, list):
                    return self._normalise_entries(candidates)

        snippet = str(result)[:200]
        raise AgentOutputError(
            "Character agent must return a JSON list; received: " + snippet
        )

    def _normalise_entries(
        self,
        entries: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        normalised: List[Dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            clone: Dict[str, Any] = dict(entry)
            for field in ("name", "intent", "action", "speech"):
                value = clone.get(field)
                if not isinstance(value, str):
                    if value is None:
                        clone[field] = "" if field != "name" else "Unknown"
                    else:
                        clone[field] = str(value)
                if field == "speech" and len(clone[field]) > MAX_SPEECH_LENGTH:
                    clone[field] = clone[field][:MAX_SPEECH_LENGTH]
            effects_raw = clone.get("effects")
            effects: Dict[str, Any] = (
                dict(effects_raw) if isinstance(effects_raw, dict) else {}
            )

            trust_delta = effects.get("trust_delta")
            if trust_delta not in (-1, 0, 1):
                effects.pop("trust_delta", None)

            flag_set = effects.get("flag_set")
            if isinstance(flag_set, list):
                cleaned_flags = []
                for flag in flag_set:
                    if isinstance(flag, (str, int, float)):
                        text = str(flag).strip()
                        if text:
                            cleaned_flags.append(text)
                if cleaned_flags:
                    effects["flag_set"] = cleaned_flags
                else:
                    effects.pop("flag_set", None)
            else:
                effects.pop("flag_set", None)

            item_change = effects.get("item_change")
            if isinstance(item_change, dict):
                item = item_change.get("item")
                delta = item_change.get("delta")
                target = item_change.get("target")
                if not item or delta not in (-1, 1) or not target:
                    effects.pop("item_change", None)
                else:
                    effects["item_change"] = {
                        "item": str(item),
                        "delta": int(delta),
                        "target": str(target),
                    }
            else:
                effects.pop("item_change", None)

            status_change = effects.get("status_change")
            if isinstance(status_change, dict):
                target = status_change.get("target")
                status = status_change.get("status")
                duration = status_change.get("duration")
                if not target or not status:
                    effects.pop("status_change", None)
                else:
                    safe_duration = 0
                    if isinstance(duration, (int, float)):
                        safe_duration = int(duration)
                    effects["status_change"] = {
                        "target": str(target),
                        "status": str(status),
                        "duration": max(0, safe_duration),
                    }
            else:
                effects.pop("status_change", None)

            clone["effects"] = effects

            # Safe functions: normalize if present and valid
            safe_functions = clone.get("safe_functions")
            if isinstance(safe_functions, list):
                cleaned = []
                for sf in safe_functions:
                    if not isinstance(sf, dict):
                        continue
                    name = sf.get("name")
                    args = sf.get("args", [])
                    kwargs = sf.get("kwargs", {})
                    metadata = sf.get("metadata", {})
                    if not isinstance(name, str) or not name.strip():
                        continue
                    if not isinstance(args, list):
                        args = []
                    if not isinstance(kwargs, dict):
                        kwargs = {}
                    if not isinstance(metadata, dict):
                        metadata = {}
                    cleaned.append(
                        {
                            "name": name.strip(),
                            "args": args,
                            "kwargs": kwargs,
                            "metadata": metadata,
                        }
                    )
                if cleaned:
                    clone["safe_functions"] = cleaned
                else:
                    clone.pop("safe_functions", None)
            else:
                clone.pop("safe_functions", None)

            normalised.append(clone)
        return normalised
