"""Utility client for interacting with a local Ollama server."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
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
    # Large timeout to avoid premature cancellations in local dev.
    timeout: float = 1e6

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

    def list_models(self) -> list[str]:
        """Return a normalized list of available model ids/names from Ollama.

        This handles different response shapes from Ollama (e.g. OpenAI-like
        list or Ollama's `{"object":"list","data":[...]}` format).
        """
        url = urljoin(self._config.normalize_base_url(), "v1/models")
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=self._config.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise OllamaClientError(
                f"Ollama returned HTTP {exc.code}: {detail}"
            ) from exc
        except error.URLError as exc:
            raise OllamaClientError(
                f"Cannot reach Ollama server: {exc.reason}"
            ) from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(
                "Ollama returned invalid JSON for models list"
            ) from exc

        models = self._normalize_models_payload(payload)
        return models

    def _normalize_models_payload(self, payload: Any) -> list[str]:
        """Normalize various `/v1/models` payload shapes into a list of ids.

        Handles cases such as:
        - {'object':'list','data':[{'id': 'model:name'}, ...]}
        - [{'model': 'name'}, {'name':'...'}]
        """
        names: set[str] = set()
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    name = entry.get("id") or entry.get("model") or entry.get("name")
                    if name:
                        names.add(str(name))
            else:
                # Fallback: try to extract top-level fields that look like models
                for key in ("model", "id", "name"):
                    val = payload.get(key)
                    if isinstance(val, str):
                        names.add(val)
        elif isinstance(payload, list):
            for entry in payload:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("model") or entry.get("name") or entry.get("id")
                if name:
                    names.add(str(name))
        return sorted(names)


def generate_with_timeout(
    client: OllamaClient,
    *,
    # Use a very large default to emulate no timeout locally.
    timeout_seconds: float = 1e6,
    max_retries: int = 1,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Call `client.generate` while enforcing a timeout + retry policy."""

    attempts = max(1, int(max_retries) + 1)
    last_error: Exception | None = None
    for attempt in range(attempts):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(client.generate, **kwargs)
            try:
                return future.result(timeout=timeout_seconds)
            except FutureTimeout:
                future.cancel()
                last_error = TimeoutError(
                    f"Ollama call exceeded {timeout_seconds:.2f}s (attempt {attempt + 1}/{attempts})"
                )
            except Exception:
                # Surface any other error immediately.
                raise
    if last_error is None:
        last_error = TimeoutError(
            f"Ollama call exceeded {timeout_seconds:.2f}s after {attempts} attempts"
        )
    raise last_error


__all__ = [
    "OllamaClient",
    "OllamaClientConfig",
    "OllamaClientError",
    "generate_with_timeout",
]
