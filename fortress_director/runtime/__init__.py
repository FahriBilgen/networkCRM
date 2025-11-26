from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional

import yaml

from fortress_director.llm import runtime_mode
import fortress_director.llm.cache as llm_cache
import fortress_director.settings as settings_module
from fortress_director.settings import LLMRuntimeConfig

LOGGER = logging.getLogger(__name__)
TRACE_LIMIT_BYTES = 200 * 1024
NPC_MOVE_LIMIT = 1


@dataclass(frozen=True)
class DemoLLMConfig:
    timeout_seconds: float = 10.0
    cache_ttl_seconds: int = 0
    enable_cache: bool = False
    max_retries: int = 0


@dataclass(frozen=True)
class DemoRuntimeConfig:
    log_level: str = "INFO"
    allow_reset: bool = True
    demo_scripted_fallbacks: bool = True


@dataclass(frozen=True)
class DemoUIConfig:
    auto_open_browser: bool = True


@dataclass(frozen=True)
class DemoConfig:
    mode: str
    llm: DemoLLMConfig
    runtime: DemoRuntimeConfig
    ui: DemoUIConfig


_DEMO_CONFIG: DemoConfig | None = None


def load_demo_config_if_exists(path: str | Path) -> DemoConfig | None:
    """Load demo config from disk if present and apply runtime overrides."""

    config_path = Path(path)
    if not config_path.exists():
        return None
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        LOGGER.warning("Failed to parse %s: %s", config_path, exc)
        return None
    if not isinstance(payload, Mapping):
        LOGGER.warning("Demo config at %s is not a mapping", config_path)
        return None
    config = DemoConfig(
        mode=str(payload.get("mode") or "demo"),
        llm=_build_llm_block(payload.get("llm") or {}),
        runtime=_build_runtime_block(payload.get("runtime") or {}),
        ui=_build_ui_block(payload.get("ui") or {}),
    )
    _apply_demo_settings(config)
    return config


def _build_llm_block(raw: Mapping[str, Any]) -> DemoLLMConfig:
    return DemoLLMConfig(
        timeout_seconds=float(raw.get("timeout_seconds", 10)),
        cache_ttl_seconds=int(raw.get("cache_ttl_seconds", 0)),
        enable_cache=bool(raw.get("enable_cache", False)),
        max_retries=int(raw.get("max_retries", 0)),
    )


def _build_runtime_block(raw: Mapping[str, Any]) -> DemoRuntimeConfig:
    return DemoRuntimeConfig(
        log_level=str(raw.get("log_level", "INFO")),
        allow_reset=bool(raw.get("allow_reset", True)),
        demo_scripted_fallbacks=bool(raw.get("demo_scripted_fallbacks", True)),
    )


def _build_ui_block(raw: Mapping[str, Any]) -> DemoUIConfig:
    return DemoUIConfig(
        auto_open_browser=bool(raw.get("auto_open_browser", True)),
    )


def _apply_demo_settings(config: DemoConfig) -> None:
    global _DEMO_CONFIG
    _DEMO_CONFIG = config
    runtime_mode.set_demo_mode(config.mode.lower() == "demo")
    if config.runtime.demo_scripted_fallbacks:
        runtime_mode.set_llm_enabled(False)
    _override_llm_runtime(config.llm)


def _override_llm_runtime(llm: DemoLLMConfig) -> None:
    current = settings_module.SETTINGS.llm_runtime
    runtime_override = LLMRuntimeConfig(
        timeout_seconds=llm.timeout_seconds,
        cache_ttl_seconds=llm.cache_ttl_seconds,
        max_retries=llm.max_retries,
        enable_cache=llm.enable_cache,
        log_metrics=current.log_metrics,
    )
    settings_module.SETTINGS = replace(
        settings_module.SETTINGS, llm_runtime=runtime_override
    )
    llm_cache.DEFAULT_CACHE.ttl = llm.cache_ttl_seconds
    _safe_clear_cache(llm_cache.DEFAULT_CACHE)


def _safe_clear_cache(cache: llm_cache.LLMCache) -> None:
    store: MutableMapping[str, Any] = getattr(cache, "_store", {})
    if isinstance(store, MutableMapping):
        store.clear()


def get_demo_config() -> DemoConfig | None:
    return _DEMO_CONFIG


def is_demo_mode_active() -> bool:
    return _DEMO_CONFIG is not None and runtime_mode.get_mode() == runtime_mode.DEMO_MODE


def limit_npc_positions(positions: Dict[str, Any]) -> Dict[str, Any]:
    if not (is_demo_mode_active() and positions):
        return positions
    limited: Dict[str, Any] = {}
    for key in sorted(positions.keys())[:NPC_MOVE_LIMIT]:
        limited[key] = positions[key]
    return limited


def ensure_demo_atmosphere(
    atmosphere: Optional[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    if not is_demo_mode_active():
        return atmosphere
    if atmosphere:
        return atmosphere
    return {
        "id": "demo_siege_night",
        "description": "Lantern-lit ramparts under constant siege pressure.",
        "palette": ["#171717", "#ffb347"],
        "ambient_track": "siege_drums_low",
    }


def compact_trace_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not is_demo_mode_active():
        return payload
    serialized = json.dumps(payload, ensure_ascii=False)
    if len(serialized.encode("utf-8")) <= TRACE_LIMIT_BYTES:
        return payload
    trimmed = dict(payload)
    trimmed.setdefault("_demo_trace_note", "")
    trimmed_fields: list[str] = []
    for key in (
        "render_payload",
        "projected_state",
        "director_output",
        "planner_output",
        "executed_actions",
        "state_delta",
    ):
        if key in trimmed:
            trimmed[key] = f"<omitted: {key} trimmed for demo mode>"
            trimmed_fields.append(key)
            serialized = json.dumps(trimmed, ensure_ascii=False)
            if len(serialized.encode("utf-8")) <= TRACE_LIMIT_BYTES:
                break
    note = (
        f"Trace trimmed for demo mode to {TRACE_LIMIT_BYTES // 1024}KB."
        if trimmed_fields
        else f"Trace capped at {TRACE_LIMIT_BYTES // 1024}KB for demo mode."
    )
    if trimmed.get("_demo_trace_note"):
        trimmed["_demo_trace_note"] += " " + note
    else:
        trimmed["_demo_trace_note"] = note
    return trimmed


def get_trace_limit_bytes() -> int:
    return TRACE_LIMIT_BYTES


__all__ = [
    "DemoConfig",
    "ensure_demo_atmosphere",
    "limit_npc_positions",
    "load_demo_config_if_exists",
    "get_demo_config",
    "is_demo_mode_active",
    "compact_trace_payload",
    "get_trace_limit_bytes",
]
