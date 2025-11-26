from __future__ import annotations

from typing import Any, Dict

from fortress_director.core.function_registry import bind_handler, load_defaults
from fortress_director.core.state_store import GameState

load_defaults()


def _response(
    log: str,
    *,
    status: str = "applied",
    metrics: Dict[str, int] | None = None,
    effects: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "status": status,
        "log": log,
        "metrics": metrics or {},
        "effects": effects or {},
    }


def adjust_metric_handler(
    game_state: GameState, metric: str, delta: int, cause: str | None = None
) -> Dict[str, Any]:
    new_value = game_state.adjust_metric(metric, int(delta))
    log = f"{metric} adjusted by {delta}."
    if cause:
        log = f"{log} Cause: {cause}."
    return _response(log, metrics={metric: int(delta)}, effects={metric: new_value})


def log_message_handler(
    game_state: GameState, message: str, severity: str | None = None
) -> Dict[str, Any]:
    prefix = f"[{severity.upper()}] " if severity else ""
    entry = f"{prefix}{message}"
    game_state.add_log_entry(entry)
    return _response(entry)


def tag_state_handler(game_state: GameState, tag: str) -> Dict[str, Any]:
    game_state.add_state_tag(tag)
    log = f"State tagged with '{tag}'."
    return _response(log, effects={"tag": tag})


def set_flag_handler(game_state: GameState, flag: str) -> Dict[str, Any]:
    game_state.set_flag(flag)
    log = f"Flag '{flag}' enabled."
    return _response(log, effects={"flag": flag})


def clear_flag_handler(game_state: GameState, flag: str) -> Dict[str, Any]:
    game_state.clear_flag(flag)
    log = f"Flag '{flag}' cleared."
    return _response(log, effects={"flag": flag})


bind_handler("adjust_metric", adjust_metric_handler)
bind_handler("log_message", log_message_handler)
bind_handler("tag_state", tag_state_handler)
bind_handler("set_flag", set_flag_handler)
bind_handler("clear_flag", clear_flag_handler)
