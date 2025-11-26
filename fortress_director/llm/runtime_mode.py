"""Global runtime switch controlling whether agents call live LLMs."""

from __future__ import annotations

import os
from typing import Mapping

_LLM_ENABLED = True
_MODE_OVERRIDE: str | None = None
_MODE_ENV = "FORTRESS_LLM_MODE"
_OFFLINE_ENV = "FORTRESS_OFFLINE"
DEMO_MODE = "demo"


def is_llm_enabled() -> bool:
    """Return True if live LLM calls are enabled."""

    return _LLM_ENABLED


def set_llm_enabled(enabled: bool) -> None:
    """Enable or disable live LLM calls."""

    global _LLM_ENABLED
    _LLM_ENABLED = bool(enabled)


def get_mode() -> str:
    """Return a short string describing the current mode."""

    if _MODE_OVERRIDE:
        return _MODE_OVERRIDE
    return "llm" if is_llm_enabled() else "stub"


def set_demo_mode(enabled: bool) -> None:
    """Toggle the demo override flag.

    Kept above `load_runtime_mode_from_env` so it can be referenced
    during module import-time initialization.
    """

    global _MODE_OVERRIDE
    if enabled:
        _MODE_OVERRIDE = DEMO_MODE
    elif _MODE_OVERRIDE == DEMO_MODE:
        _MODE_OVERRIDE = None


def load_runtime_mode_from_env(environ: Mapping[str, str] | None = None) -> None:
    """Initialize runtime mode based on environment variables."""

    env = environ or os.environ
    raw_mode = (env.get(_MODE_ENV) or "").strip().lower()
    offline_flag = (env.get(_OFFLINE_ENV) or "0").strip() == "1"

    if raw_mode == DEMO_MODE:
        set_demo_mode(True)
        set_llm_enabled(False)
    else:
        set_demo_mode(False)
    if raw_mode in {"stub", "offline", "disabled", "0"} or offline_flag:
        set_llm_enabled(False)
    elif raw_mode in {"llm", "live", "1"}:
        set_llm_enabled(True)
    elif not raw_mode:
        # Default: prefer LLM mode unless explicit offline toggle is set.
        set_llm_enabled(not offline_flag)
    # Any other value leaves the current state untouched so callers can set it manually.


# Ensure module import honors environment configuration.
load_runtime_mode_from_env()


__all__ = [
    "DEMO_MODE",
    "get_mode",
    "is_llm_enabled",
    "set_llm_enabled",
    "set_demo_mode",
    "load_runtime_mode_from_env",
]
