"""Common agent helpers for Fortress Director."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from llm.ollama_client import (
    OllamaClient,
    OllamaClientConfig,
    OllamaClientError,
)
from settings import ModelConfig, SETTINGS


class AgentError(RuntimeError):
    """Base class for agent-related failures."""


class AgentOutputError(AgentError):
    """Raised when an agent returns invalid JSON."""


@dataclass
class PromptTemplate:
    """Small helper to load and render prompt templates."""

    path: Path
    cache: bool = True
    _cached_value: Optional[str] = field(default=None, init=False, repr=False)

    def load(self) -> str:
        if self.cache and self._cached_value is not None:
            return self._cached_value
        value = self.path.read_text(encoding="utf-8")
        if self.cache:
            self._cached_value = value
        return value

    def render(self, **kwargs: Any) -> str:
        try:
            return self.load().format(**kwargs)
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise AgentError(f"Missing prompt variable: {exc}") from exc


class BaseAgent:
    """Reusable logic for invoking Ollama-backed agents."""

    def __init__(
        self,
        *,
        name: str,
        prompt_template: PromptTemplate,
        model_config: ModelConfig,
        client: Optional[OllamaClient] = None,
        expects_json: bool = True,
    ) -> None:
        self.name = name
        self._template = prompt_template
        self._model = model_config
        self._client = client or OllamaClient()
        self._expects_json = expects_json

    def run(
        self,
        *,
        variables: Dict[str, Any],
        options_override: Optional[Dict[str, Any]] = None,
    ) -> Any:
        prompt = self._template.render(**variables)
        options = self._build_options(options_override)
        try:
            response = self._client.generate(
                model=self._model.name,
                prompt=prompt,
                options=options,
                response_format="json" if self._expects_json else None,
            )
        except OllamaClientError as exc:
            raise AgentError(f"{self.name} agent failed: {exc}") from exc

        text = response.get("response", "").strip()
        if not self._expects_json:
            return text
        return self._parse_json(text)

    def _build_options(
        self,
        options_override: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        options: Dict[str, Any] = {
            "temperature": self._model.temperature,
            "top_p": self._model.top_p,
            "num_predict": self._model.max_tokens,
        }
        if options_override:
            options.update(options_override)
        return options

    def _parse_json(self, text: str) -> Any:
        if not text:
            raise AgentOutputError(f"{self.name} agent returned empty output")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise AgentOutputError(
                f"{self.name} agent produced invalid JSON: {text}"
            ) from exc


def build_prompt_path(filename: str) -> Path:
    """Resolve a prompt file relative to the project root."""

    return SETTINGS.project_root / "prompts" / filename


def default_ollama_client() -> OllamaClient:
    """Create an Ollama client configured from global settings."""

    config = OllamaClientConfig(
        base_url=SETTINGS.ollama_base_url,
        timeout=SETTINGS.ollama_timeout,
    )
    return OllamaClient(config)


def get_model_config(agent_key: str) -> ModelConfig:
    """Fetch model configuration for the requested agent type."""

    try:
        return SETTINGS.models[agent_key]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise AgentError(f"Unknown agent key: {agent_key}") from exc
