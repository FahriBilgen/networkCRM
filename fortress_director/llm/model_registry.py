"""Simple utilities for managing agent-to-model mappings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping

from fortress_director.settings import SETTINGS, LLMOptions, ModelConfig


@dataclass(frozen=True)
class ModelRecord:
    """Resolved model metadata plus helper methods for logging."""

    agent: str
    config: ModelConfig

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "agent": self.agent,
            "name": self.config.name,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "max_tokens": self.config.max_tokens,
        }
        if self.config.top_k is not None:
            payload["top_k"] = self.config.top_k
        return payload


class ModelRegistry:
    """In-memory registry mapping agent keys to generation configs."""

    def __init__(
        self,
        models: Mapping[str, ModelConfig],
        default_options: LLMOptions | None = None,
    ) -> None:
        self._models: Dict[str, ModelConfig] = {
            key.lower(): value for key, value in models.items()
        }
        self._defaults = default_options or LLMOptions()

    def get(self, agent_key: str) -> ModelConfig:
        """Return the model config for *agent_key*."""

        key = agent_key.lower()
        if key not in self._models:
            raise KeyError(f"Unknown agent model: {agent_key}")
        return self._models[key]

    def list(self) -> Iterable[ModelRecord]:
        """Yield ModelRecord entries for all registered agents."""

        for agent, config in self._models.items():
            yield ModelRecord(agent=agent, config=config)

    def build_generation_options(
        self,
        agent_key: str,
        *,
        overrides: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Return Ollama-compatible options for *agent_key*."""

        config = self.get(agent_key)
        options: Dict[str, Any] = {
            "temperature": config.temperature,
            "top_p": config.top_p,
        }
        top_k = config.top_k if config.top_k is not None else self._defaults.top_k
        if top_k is not None:
            options["top_k"] = top_k
        if config.max_tokens:
            options["num_predict"] = int(config.max_tokens)
        if overrides:
            options.update(overrides)
        return options


CORE_AGENT_KEYS = ("director", "planner", "world_renderer")
DEFAULT_MODELS: Dict[str, ModelConfig] = {
    key: SETTINGS.models[key] for key in CORE_AGENT_KEYS if key in SETTINGS.models
}
DEFAULT_REGISTRY = ModelRegistry(DEFAULT_MODELS, SETTINGS.llm_options)


def get_registry() -> ModelRegistry:
    """Return the singleton registry for simplified agents."""

    return DEFAULT_REGISTRY
