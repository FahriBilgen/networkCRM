"""Helpers for timing LLM calls and surfacing call metadata."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

from fortress_director.settings import SETTINGS

LOG_PATH = SETTINGS.log_dir / "llm_calls.log"


@dataclass(frozen=True)
class LLMCallMetrics:
    """Structured metadata describing a single LLM invocation."""

    agent: str
    model_name: str
    duration_ms: float
    prompt_tokens: int | None
    completion_tokens: int | None
    success: bool
    error_type: str | None = None


def profile_llm_call(
    agent: str,
    model_name: str,
    fn: Callable[[], Any],
) -> Tuple[Any | None, LLMCallMetrics]:
    """Execute *fn* while capturing timing + success information."""

    start = time.perf_counter()
    success = True
    error_type = None
    result: Any | None = None
    try:
        result = fn()
    except Exception as exc:  # pragma: no cover - exercised via tests
        success = False
        error_type = exc.__class__.__name__
    end = time.perf_counter()
    metrics = LLMCallMetrics(
        agent=agent,
        model_name=model_name,
        duration_ms=(end - start) * 1000.0,
        prompt_tokens=None,
        completion_tokens=None,
        success=success,
        error_type=error_type,
    )
    return result, metrics


def summarize_llm_log(limit: int | None = None) -> Dict[str, Any]:
    """Aggregate JSON line metrics log for quick summaries."""

    if not LOG_PATH.exists():
        return {"total_calls": 0, "per_agent": {}}
    with LOG_PATH.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    if limit is not None and limit > 0:
        lines = lines[-limit:]
    per_agent: Dict[str, list[float]] = {}
    total = 0
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        agent = str(payload.get("agent") or "unknown")
        duration = float(payload.get("duration_ms") or 0.0)
        per_agent.setdefault(agent, []).append(duration)
        total += 1
    return {
        "total_calls": total,
        "per_agent": {
            agent: {
                "count": len(values),
                "avg_ms": (sum(values) / len(values)) if values else 0.0,
                "max_ms": max(values) if values else 0.0,
            }
            for agent, values in per_agent.items()
        },
    }


__all__ = ["LLMCallMetrics", "profile_llm_call", "summarize_llm_log"]
