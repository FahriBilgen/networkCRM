"""Final sequence safe functions that are only invoked during the finale."""

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


def trigger_mass_evacuate_handler(game_state: GameState) -> Dict[str, Any]:
    snapshot = game_state.snapshot()
    civilians = max(20, len(snapshot.get("npc_locations") or []) * 12)
    morale_boost = max(2, civilians // 50)
    game_state.adjust_metric("morale", morale_boost)
    game_state.set_flag("final_evacuation_complete")
    log = f"Emergency convoys escort {civilians} civilians out of the fortress."
    return _response(
        log,
        metrics={"morale": morale_boost},
        effects={"civilians_evacuated": civilians},
    )


def collapse_structure_handler(game_state: GameState, structure_id: str) -> Dict[str, Any]:
    struct = game_state.adjust_structure_integrity(structure_id, -500)
    struct = game_state.update_structure(structure_id, status="collapsed")
    log = f"{structure_id} collapses in the final push."
    return _response(
        log,
        effects={"structure_id": struct.id, "status": struct.status, "integrity": struct.integrity},
    )


def ignite_structure_handler(game_state: GameState, structure_id: str) -> Dict[str, Any]:
    struct = game_state.update_structure(structure_id, on_fire=True, status="burning")
    morale_delta = -3
    game_state.adjust_metric("morale", morale_delta)
    log = f"Flames race across {structure_id}, casting the finale in firelight."
    return _response(
        log,
        metrics={"morale": morale_delta},
        effects={"structure_id": struct.id, "on_fire": struct.on_fire},
    )


def spawn_fire_effect_handler(game_state: GameState, x: int, y: int) -> Dict[str, Any]:
    marker = game_state.add_event_marker(
        x=int(x),
        y=int(y),
        severity=3,
        description="Finale inferno engulfs the battlements.",
        entity_type="fire",
    )
    return _response(
        "Inferno marker spawned.",
        effects={"marker_id": marker.id, "position": {"x": marker.x, "y": marker.y}},
    )


def spawn_smoke_effect_handler(game_state: GameState, x: int, y: int) -> Dict[str, Any]:
    marker = game_state.add_event_marker(
        x=int(x),
        y=int(y),
        severity=2,
        description="Thick smoke blankets the final battlefield.",
        entity_type="smoke",
    )
    return _response(
        "Smoke effect spreads across the map.",
        effects={"marker_id": marker.id, "position": {"x": marker.x, "y": marker.y}},
    )


def spawn_mass_enemy_wave_handler(
    game_state: GameState,
    direction: str,
    strength: int,
) -> Dict[str, Any]:
    penalty = -max(2, abs(int(strength)) // 3)
    stability = game_state.adjust_world_stat("stability", penalty)
    game_state.set_flag(f"enemy_wave_{direction}")
    log = f"Mass enemy wave surges from the {direction}; stability {stability}."
    return _response(
        log,
        metrics={"stability": penalty},
        effects={"direction": direction, "strength": int(strength)},
    )


def boost_allied_morale_handler(game_state: GameState, delta: int) -> Dict[str, Any]:
    boost = max(1, int(delta))
    morale = game_state.adjust_metric("morale", boost)
    log = f"Allied morale surges by {boost} during the finale."
    return _response(
        log,
        metrics={"morale": boost},
        effects={"morale": morale},
    )


def freeze_weather_handler(game_state: GameState, duration: int) -> Dict[str, Any]:
    payload = {
        "weather_pattern": {
            "pattern": "frozen",
            "remaining": max(0, int(duration)),
            "lock_until": game_state.turn + max(0, int(duration)),
        }
    }
    game_state.apply_delta(payload)
    log = "Shock frost freezes the battlefield, stilling the storm."
    return _response(
        log,
        effects=payload["weather_pattern"],
    )


def global_blackout_handler(game_state: GameState) -> Dict[str, Any]:
    payload = {
        "world": {
            "threat_level": "blackout",
        },
        "flags": ["global_blackout"],
    }
    game_state.apply_delta(payload)
    log = "Citadel systems blackout; only silhouettes remain."
    return _response(log, effects={"threat_level": "blackout"})


def npc_final_move_handler(game_state: GameState, npc_id: str, x: int, y: int) -> Dict[str, Any]:
    npc = game_state.move_npc(npc_id, int(x), int(y))
    log = f"{npc.name} takes a final position at ({npc.x}, {npc.y})."
    return _response(
        log,
        effects={"npc_id": npc.id, "position": {"x": npc.x, "y": npc.y}},
    )


bind_handler("trigger_mass_evacuate", trigger_mass_evacuate_handler)
bind_handler("collapse_structure", collapse_structure_handler)
bind_handler("ignite_structure", ignite_structure_handler)
bind_handler("spawn_fire_effect", spawn_fire_effect_handler)
bind_handler("spawn_smoke_effect", spawn_smoke_effect_handler)
bind_handler("spawn_mass_enemy_wave", spawn_mass_enemy_wave_handler)
bind_handler("boost_allied_morale", boost_allied_morale_handler)
bind_handler("freeze_weather", freeze_weather_handler)
bind_handler("global_blackout", global_blackout_handler)
bind_handler("npc_final_move", npc_final_move_handler)
