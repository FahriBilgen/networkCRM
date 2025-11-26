"""Domain-aware safe function executor backed by the new registry."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from fortress_director.core.function_registry import (
    get_safe_function,
    load_defaults,
)
from fortress_director.core.state_store import GameState

# Import category handlers for their side effects (bind_handler registrations).
from fortress_director.core.functions.impl import (  # noqa: F401
    combat as _combat_impl,
    economy as _economy_impl,
    event as _event_impl,
    morale as _morale_impl,
    npc as _npc_impl,
    structure as _structure_impl,
    utility as _utility_impl,
)
from fortress_director.core import final_safe_functions  # noqa: F401

Action = Dict[str, Any]
ActionTelemetry = Dict[str, Any]


def apply_actions(game_state: GameState, actions: List[Action]) -> Dict[str, Any]:
    """Apply planned actions to the state and return telemetry + delta."""

    load_defaults()
    before_state = game_state.snapshot()
    executed: List[ActionTelemetry] = []
    logs: List[str] = []
    for idx, action in enumerate(actions or []):
        telemetry = _execute_action(game_state, action, idx)
        executed.append(telemetry)
        logs.append(telemetry["log"])
    if not actions:
        logs.append("No planned actions executed.")
    world_state = game_state.apply_delta({"turn": 1, "log": logs})
    state_delta = GameState.compute_state_delta(before_state, world_state)
    state_delta["turn_advanced"] = True
    state_delta["log_entries"] = logs
    state_delta.update(_build_projection_delta(game_state, before_state, world_state))
    return {
        "world_state": world_state,
        "executed_actions": executed,
        "state_delta": state_delta,
    }


def _execute_action(
    game_state: GameState, action: Action, index: int
) -> ActionTelemetry:
    name = str(action.get("function") or f"action_{index}")
    args = dict(action.get("args") or {})
    meta = get_safe_function(name)
    if meta is None:
        return {
            "function": name,
            "args": args,
            "status": "error",
            "log": f"{name} is not a registered safe function.",
            "metrics": {},
            "effects": {},
        }
    _validate_params(meta.name, meta.params, args)
    if meta.handler is None:
        return {
            "function": name,
            "args": args,
            "status": "error",
            "log": f"{name} has no bound handler.",
            "metrics": {},
            "effects": {},
        }
    try:
        result = meta.handler(game_state, **args)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "function": name,
            "args": args,
            "status": "error",
            "log": f"{name} failed: {exc}",
            "metrics": {},
            "effects": {},
        }
    return {
        "function": name,
        "args": args,
        "status": result.get("status", "applied"),
        "log": result.get("log", f"{name} executed."),
        "metrics": result.get("metrics", {}),
        "effects": result.get("effects", {}),
    }


def _validate_params(
    name: str,
    params: Iterable,
    provided: Dict[str, Any],
) -> None:
    required = {param.name for param in params if getattr(param, "required", True)}
    optional = {param.name for param in params if not getattr(param, "required", True)}
    allowed = required | optional
    missing = [field for field in required if field not in provided]
    if missing:
        raise ValueError(f"{name} missing parameters: {', '.join(missing)}")
    unknown = [key for key in provided if key not in allowed]
    if unknown:
        raise ValueError(f"{name} received unexpected parameters: {', '.join(unknown)}")


def _build_projection_delta(
    game_state: GameState,
    before_state: Dict[str, Any],
    world_state: Dict[str, Any],
) -> Dict[str, Any]:
    snapshot = game_state.as_domain()
    structures = snapshot.structure_integrities()
    wall_integrity: Dict[str, Dict[str, Any]] = {}
    for struct_id, payload in structures.items():
        if "wall" in payload.get("kind", "") or "wall" in struct_id:
            wall_integrity[struct_id] = {"integrity": payload.get("integrity", 0)}
    morale_change = _metric_delta(before_state, world_state, "morale")
    resource_change = _metric_delta(before_state, world_state, "resources")
    return {
        "npc_positions": snapshot.npc_positions(),
        "event_markers": snapshot.event_list(),
        "wall_integrity": wall_integrity,
        "morale_change": morale_change,
        "resource_change": resource_change,
    }


def _metric_delta(
    previous: Dict[str, Any],
    new_state: Dict[str, Any],
    metric: str,
) -> int:
    before = int((previous.get("metrics") or {}).get(metric, 0) or 0)
    after = int((new_state.get("metrics") or {}).get(metric, 0) or 0)
    return after - before
