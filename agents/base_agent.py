"""Common agent helpers for Fortress Director."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from llm.ollama_client import (
    OllamaClient,
    OllamaClientConfig,
    OllamaClientError,
)
from settings import ModelConfig, SETTINGS
from utils.agent_monitor import AGENT_MONITOR


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

    @property
    def text(self) -> str:
        return self.load()

    @text.setter
    def text(self, value: str) -> None:
        self._cached_value = value


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

    @property
    def prompt_template(self) -> PromptTemplate:
        return self._template

    def run(
        self,
        *,
        variables: Dict[str, Any],
        options_override: Optional[Dict[str, Any]] = None,
    ) -> Any:
        start_time = time.time()
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
            AGENT_MONITOR.record_failure(self.name, "api_error")
            raise AgentError(f"{self.name} agent failed: {exc}") from exc

        end_time = time.time()
        response_time = end_time - start_time
        AGENT_MONITOR.record_response_time(self.name, response_time)

        text = response.get("response", "").strip()
        if not self._expects_json:
            AGENT_MONITOR.record_success(self.name)
            return text

        parsed = self._parse_json(text)
        self._validate_output_quality(parsed)
        AGENT_MONITOR.record_success(self.name)
        return parsed

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

    def _validate_output_quality(self, output: Any) -> None:
        """Validate agent output quality and consistency."""
        from utils.output_validator import (
            validate_agent_output_consistency,
            validate_character_output_quality,
            validate_event_output_quality,
        )

        # Convert output to string for consistency checking
        if isinstance(output, dict):
            output_str = json.dumps(output)
        elif isinstance(output, list):
            output_str = json.dumps(output)
        else:
            output_str = str(output)

        # Check for physical impossibilities and inconsistencies
        if not validate_agent_output_consistency(output_str):
            AGENT_MONITOR.record_failure(self.name, "consistency_violation")
            raise AgentOutputError(
                f"{self.name} agent output contains consistency violations: {output_str[:200]}..."
            )

        # Agent-specific quality validation
        if self.name == "character" and isinstance(output, list):
            for reaction in output:
                if not validate_character_output_quality(reaction):
                    AGENT_MONITOR.record_failure(self.name, "quality_issue")
                    raise AgentOutputError(
                        f"{self.name} agent output quality issues in reaction: {reaction}"
                    )
        elif self.name == "event" and isinstance(output, dict):
            if not validate_event_output_quality(output):
                AGENT_MONITOR.record_failure(self.name, "quality_issue")
                raise AgentOutputError(
                    f"{self.name} agent output quality issues: {output}"
                )

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


def default_ollama_client(agent_key: Optional[str] = None) -> OllamaClient:
    """Create an Ollama client that always talks to a live model service."""

    base_url = os.environ.get("FORTRESS_OLLAMA_BASE_URL", SETTINGS.ollama_base_url)
    timeout_value = os.environ.get("FORTRESS_OLLAMA_TIMEOUT")
    try:
        timeout = (
            float(timeout_value)
            if timeout_value is not None
            else SETTINGS.ollama_timeout
        )
    except ValueError as exc:  # pragma: no cover - defensive guard
        raise AgentError("FORTRESS_OLLAMA_TIMEOUT must be a float value") from exc

    config = OllamaClientConfig(
        base_url=base_url,
        timeout=timeout,
    )
    return OllamaClient(config)


def get_model_config(agent_key: str) -> ModelConfig:
    """Fetch model configuration for the requested agent type."""

    try:
        return SETTINGS.models[agent_key]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise AgentError(f"Unknown agent key: {agent_key}") from exc
