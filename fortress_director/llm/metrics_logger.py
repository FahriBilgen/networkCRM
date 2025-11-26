"""Append-only logging utilities for LLM call metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List

from fortress_director.llm.profiler import LLMCallMetrics
from fortress_director.settings import SETTINGS

LOG_PATH = SETTINGS.log_dir / "llm_calls.log"
_CALLBACKS: List[Callable[[LLMCallMetrics], None]] = []


def log_llm_metrics(metrics: LLMCallMetrics) -> None:
    """Serialize *metrics* as a JSON line for later analysis."""

    path = LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "agent": metrics.agent,
        "model": metrics.model_name,
        "duration_ms": round(metrics.duration_ms, 3),
        "success": metrics.success,
        "error_type": metrics.error_type,
        "prompt_tokens": metrics.prompt_tokens,
        "completion_tokens": metrics.completion_tokens,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    for callback in list(_CALLBACKS):
        try:
            callback(metrics)
        except Exception:  # pragma: no cover - defensive guard
            continue


def register_metrics_callback(
    callback: Callable[[LLMCallMetrics], None]
) -> Callable[[], None]:
    """Register a callback invoked whenever new metrics are logged."""

    _CALLBACKS.append(callback)

    def _unsubscribe() -> None:
        try:
            _CALLBACKS.remove(callback)
        except ValueError:
            pass

    return _unsubscribe


__all__ = ["log_llm_metrics", "register_metrics_callback", "LOG_PATH"]
