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


def move_npc_handler(
    game_state: GameState, npc_id: str, x: int, y: int, room: str | None = None
) -> Dict[str, Any]:
    npc = game_state.move_npc(npc_id, x=int(x), y=int(y), room=room)
    log = f"{npc.name} relocated to ({npc.x}, {npc.y})."
    return _response(
        log,
        effects={"npc_id": npc.id, "position": {"x": npc.x, "y": npc.y}, "room": npc.room},
    )


def assign_role_handler(game_state: GameState, npc_id: str, role: str) -> Dict[str, Any]:
    npc = game_state.update_npc(npc_id, role=role)
    log = f"{npc.name} now serves as {role}."
    return _response(log, effects={"npc_id": npc.id, "role": npc.role})


def heal_npc_handler(game_state: GameState, npc_id: str, amount: int) -> Dict[str, Any]:
    npc = game_state.get_npc(npc_id)
    if npc is None:
        raise KeyError(f"NPC '{npc_id}' not found")
    new_morale = min(100, npc.morale + int(amount))
    updated = game_state.update_npc(npc_id, morale=new_morale)
    log = f"{updated.name} healed by {amount}, morale {updated.morale}."
    return _response(log, effects={"npc_id": npc_id, "morale": updated.morale})


def rest_npc_handler(game_state: GameState, npc_id: str, duration: int) -> Dict[str, Any]:
    npc = game_state.get_npc(npc_id)
    if npc is None:
        raise KeyError(f"NPC '{npc_id}' not found")
    status_effects = list(npc.status_effects)
    if "resting" not in status_effects:
        status_effects.append("resting")
    updated = game_state.update_npc(npc_id, status_effects=status_effects)
    log = f"{updated.name} rests for {duration} hours."
    return _response(log, effects={"npc_id": npc_id, "status_effects": status_effects})


def increase_npc_focus_handler(
    game_state: GameState, npc_id: str, amount: int
) -> Dict[str, Any]:
    focus = game_state.adjust_npc_focus_level(npc_id, abs(int(amount)))
    log = f"{npc_id} focus increased to {focus}."
    return _response(log, effects={"npc_id": npc_id, "focus": focus})


def reduce_npc_focus_handler(
    game_state: GameState, npc_id: str, amount: int
) -> Dict[str, Any]:
    focus = game_state.adjust_npc_focus_level(npc_id, -abs(int(amount)))
    log = f"{npc_id} focus reduced to {focus}."
    return _response(log, effects={"npc_id": npc_id, "focus": focus})


def give_equipment_handler(game_state: GameState, npc_id: str, item: str) -> Dict[str, Any]:
    items = game_state.grant_npc_equipment(npc_id, item)
    log = f"{npc_id} receives equipment: {item}."
    return _response(log, effects={"npc_id": npc_id, "equipment": items})


def send_on_patrol_handler(
    game_state: GameState, npc_id: str, duration: int
) -> Dict[str, Any]:
    game_state.set_npc_patrol(npc_id, duration)
    log = f"{npc_id} dispatched on patrol for {duration} turns."
    return _response(log, effects={"npc_id": npc_id, "patrol_duration": duration})


def return_from_patrol_handler(
    game_state: GameState, npc_id: str, report: str | None = None
) -> Dict[str, Any]:
    game_state.clear_npc_patrol(npc_id)
    if report:
        game_state.add_log_entry(f"Patrol report from {npc_id}: {report}")
    log = f"{npc_id} returns from patrol."
    return _response(
        log,
        effects={"npc_id": npc_id, "report": report},
    )


def rally_npc_handler(
    game_state: GameState, npc_id: str, message: str | None = None
) -> Dict[str, Any]:
    morale = game_state.adjust_metric("morale", 1)
    log = message or f"{npc_id} rallies nearby defenders."
    return _response(
        log,
        metrics={"morale": 1},
        effects={"npc_id": npc_id, "morale": morale},
    )


bind_handler("move_npc", move_npc_handler)
bind_handler("assign_role", assign_role_handler)
bind_handler("heal_npc", heal_npc_handler)
bind_handler("rest_npc", rest_npc_handler)
bind_handler("increase_npc_focus", increase_npc_focus_handler)
bind_handler("reduce_npc_focus", reduce_npc_focus_handler)
bind_handler("give_equipment", give_equipment_handler)
bind_handler("send_on_patrol", send_on_patrol_handler)
bind_handler("return_from_patrol", return_from_patrol_handler)
bind_handler("rally_npc", rally_npc_handler)
