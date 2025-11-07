"""Common agent helpers for Fortress Director."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from fortress_director.llm.ollama_client import (
    OllamaClient,
    OllamaClientConfig,
    OllamaClientError,
)
from fortress_director.settings import ModelConfig, SETTINGS
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
        """Expose the template contents for in-memory mutation."""

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
        """Provide access to the underlying prompt template."""

        return self._template

    def run(
        self,
        *,
        variables: Dict[str, Any],
        options_override: Optional[Dict[str, Any]] = None,
    ) -> Any:
        # Ensure commonly-required prompt variables exist to make templates
        # tolerant of callers that only pass WORLD_CONTEXT. This helps
        # integration tests which construct minimal inputs.
        vars_copy = dict(variables)
        # Provide an empty memory_layers if not present
        vars_copy.setdefault("memory_layers", [])
        # If no explicit time token was provided, try to extract it from
        # the WORLD_CONTEXT string (e.g. 'Time morning'). Fall back to
        # 'morning' to avoid raising errors in downstream agents.
        if "time" not in vars_copy or not vars_copy.get("time"):
            wc = vars_copy.get("WORLD_CONTEXT", "")
            import re

            m = re.search(r"Time\s+([^\n]+)", wc)
            if m:
                vars_copy["time"] = m.group(1).strip()
            else:
                vars_copy.setdefault("time", "morning")

        prompt = self._template.render(**vars_copy)
        options = self._build_options(options_override)
        start_time = time.perf_counter()
        try:
            response = self._client.generate(
                model=self._model.name,
                prompt=prompt,
                options=options,
                response_format="json" if self._expects_json else None,
            )
            text = response.get("response", "").strip()
            if not self._expects_json:
                result: Any = text
            else:
                result = self._parse_json(text)
        except OllamaClientError as exc:
            AGENT_MONITOR.record_failure(self.name, error_type="client_error")
            raise AgentError(f"{self.name} agent failed: {exc}") from exc
        except AgentError:
            AGENT_MONITOR.record_failure(self.name, error_type="agent_error")
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            AGENT_MONITOR.record_failure(
                self.name,
                error_type=exc.__class__.__name__,
            )
            raise
        else:
            AGENT_MONITOR.record_success(self.name)
            return result
        finally:
            elapsed = time.perf_counter() - start_time
            AGENT_MONITOR.record_response_time(self.name, elapsed)

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
