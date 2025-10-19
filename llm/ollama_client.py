"""Utility client for interacting with a local Ollama server."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional
from urllib import error, request
from urllib.parse import urljoin


class OllamaClientError(RuntimeError):
    """Raised when the Ollama server returns an error or an invalid payload."""


@dataclass(frozen=True)
class OllamaClientConfig:
    """Static configuration for the Ollama HTTP client."""

    base_url: str = "http://localhost:11434/"
    timeout: float = 60.0

    def normalize_base_url(self) -> str:
        """Ensure base URL ends with a trailing slash for urljoin semantics."""

        if self.base_url.endswith("/"):
            return self.base_url
        return f"{self.base_url}/"


class OllamaClient:
    """Very small helper around Ollama's HTTP API."""

    def __init__(self, config: Optional[OllamaClientConfig] = None) -> None:
        self._config = config or OllamaClientConfig()

    def generate(
        self,
        *,
        model: str,
        prompt: str,
        options: Optional[Dict[str, Any]] = None,
        response_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call `/api/generate` once and return the parsed JSON payload."""

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if options:
            payload["options"] = options
        if response_format:
            payload["format"] = response_format
        return self._post("/api/generate", payload)

    def chat(
        self,
        *,
        model: str,
        messages: Iterable[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        response_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invoke the `/api/chat` endpoint once and return the JSON payload."""

        payload: Dict[str, Any] = {
            "model": model,
            "messages": list(messages),
            "stream": False,
        }
        if options:
            payload["options"] = options
        if response_format:
            payload["format"] = response_format
        return self._post("/api/chat", payload)

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send a POST request to Ollama and parse the JSON response."""

        url = urljoin(self._config.normalize_base_url(), path.lstrip("/"))
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with request.urlopen(req, timeout=self._config.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            message = f"Ollama returned HTTP {exc.code}: {detail}"
            raise OllamaClientError(message) from exc
        except error.URLError as exc:
            message = f"Cannot reach Ollama server: {exc.reason}"
            raise OllamaClientError(message) from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:  # pragma: no cover
            message = "Ollama responded with invalid JSON"
            raise OllamaClientError(message) from exc
