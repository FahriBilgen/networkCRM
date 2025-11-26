from __future__ import annotations

from typing import Any, Dict, Iterable, List

from fortress_director.core.combat_engine import resolve_skirmish
from fortress_director.core.domain import NPC, Structure
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


def _positive(value: Any, default: int = 1) -> int:
    try:
        value_int = int(value)
    except (TypeError, ValueError):
        value_int = default
    return max(1, value_int)


def apply_combat_pressure_handler(game_state: GameState, intensity: int) -> Dict[str, Any]:
    pressure = _positive(intensity)
    threat = game_state.adjust_metric("threat", pressure)
    morale_delta = -max(1, pressure // 2)
    morale = game_state.adjust_metric("morale", morale_delta)
    log = f"Combat pressure intensified (threat {threat}, morale {morale})."
    return _response(log, metrics={"threat": pressure, "morale": morale_delta})


def reduce_threat_handler(game_state: GameState, amount: int) -> Dict[str, Any]:
    delta = -_positive(amount)
    threat = game_state.adjust_metric("threat", delta)
    log = f"Threat reduced by {abs(delta)} (now {threat})."
    return _response(log, metrics={"threat": delta})


def ranged_attack_handler(
    game_state: GameState, target_area: str, intensity: int
) -> Dict[str, Any]:
    volley = _positive(intensity)
    threat_delta = min(-1, -volley)
    game_state.adjust_metric("threat", threat_delta)
    game_state.add_log_entry(f"Ranged attack pounds {target_area}.")
    log = f"Archers bombard {target_area} with intensity {volley}."
    return _response(
        log,
        metrics={"threat": threat_delta},
        effects={"target_area": target_area, "volleys": volley},
    )


def melee_engagement_handler(
    game_state: GameState,
    attacker_ids: List[str],
    defender_ids: List[str],
    structure_id: str | None = None,
) -> Dict[str, Any]:
    attackers = _resolve_npcs(game_state, attacker_ids)
    defenders = _resolve_npcs(game_state, defender_ids)
    if not attackers:
        raise ValueError("at least one attacker is required")
    if not defenders:
        raise ValueError("at least one defender is required")
    structure = game_state.get_structure(structure_id) if structure_id else None
    if structure_id and structure is None:
        raise KeyError(f"Structure '{structure_id}' not found")
    outcome = resolve_skirmish(game_state, attackers, defenders, structure)
    attacker_effects = _apply_engagement_effects(
        game_state, attackers, outcome.attackers_casualties, outcome.attackers_morale_delta
    )
    defender_effects = _apply_engagement_effects(
        game_state, defenders, outcome.defenders_casualties, outcome.defenders_morale_delta
    )
    structure_effect = None
    if structure:
        updated = game_state.update_structure(
            structure.id,
            integrity=structure.integrity,
            status=_structure_status(structure),
            on_fire=structure.on_fire,
        )
        structure_effect = _serialize_structure(updated, outcome.structure_damage)
    metrics = game_state.record_combat_metrics(
        friendly_casualties=outcome.attackers_casualties,
        enemy_casualties=outcome.defenders_casualties,
    )
    return _response(
        outcome.summary,
        effects={
            "combat": {
                "attackers": attacker_effects,
                "defenders": defender_effects,
                "structure": structure_effect,
                "outcome": {
                    "attackers_casualties": outcome.attackers_casualties,
                    "defenders_casualties": outcome.defenders_casualties,
                    "structure_damage": outcome.structure_damage,
                },
            },
            "combat_metrics": metrics,
        },
    )


def suppressive_fire_handler(
    game_state: GameState, sector: str, duration: int
) -> Dict[str, Any]:
    suppression = _positive(duration)
    threat_reduction = -min(2, suppression)
    game_state.adjust_metric("threat", threat_reduction)
    game_state.adjust_world_stat("resources", -1)
    log = f"Suppressive fire pins enemies in {sector} for {suppression} turns."
    return _response(
        log,
        metrics={"threat": threat_reduction, "resources": -1},
        effects={"sector": sector, "duration": suppression},
    )


def scout_enemy_positions_handler(
    game_state: GameState, npc_id: str, direction: str
) -> Dict[str, Any]:
    game_state.set_flag(f"scouted_{direction.lower()}")
    log = f"{npc_id} scouts enemy positions toward {direction}."
    return _response(log, effects={"npc_id": npc_id, "direction": direction})


def fortify_combat_zone_handler(
    game_state: GameState, zone: str, armor_boost: int
) -> Dict[str, Any]:
    boost = _positive(armor_boost)
    game_state.adjust_metric("wall_integrity", boost)
    log = f"Combat engineers fortify {zone}, raising integrity by {boost}."
    return _response(
        log,
        metrics={"wall_integrity": boost},
        effects={"zone": zone},
    )


def deploy_archers_handler(
    game_state: GameState, x: int, y: int, volleys: int | None = None
) -> Dict[str, Any]:
    volley_count = _positive(volleys or 1)
    threat_delta = -volley_count
    game_state.adjust_metric("threat", threat_delta)
    log = f"Archers deploy to ({x}, {y}) with {volley_count} volleys."
    return _response(
        log,
        metrics={"threat": threat_delta},
        effects={"position": {"x": x, "y": y}, "volleys": volley_count},
    )


def set_ambush_handler(
    game_state: GameState,
    npc_id: str,
    x: int,
    y: int,
) -> Dict[str, Any]:
    npc = game_state.move_npc(npc_id, x=x, y=y)
    game_state.set_flag(f"ambush_{npc_id}")
    log = f"{npc.name} sets an ambush at ({npc.x}, {npc.y})."
    return _response(
        log,
        effects={"npc_id": npc.id, "position": {"x": npc.x, "y": npc.y}},
    )


def counter_attack_handler(
    game_state: GameState, force: str, focus: str
) -> Dict[str, Any]:
    morale_boost = 3
    threat_delta = -2
    game_state.adjust_metric("morale", morale_boost)
    game_state.adjust_metric("threat", threat_delta)
    log = f"{force} launches a counter-attack toward {focus}."
    return _response(
        log,
        metrics={"morale": morale_boost, "threat": threat_delta},
        effects={"force": force, "focus": focus},
    )


bind_handler("apply_combat_pressure", apply_combat_pressure_handler)
bind_handler("reduce_threat", reduce_threat_handler)
bind_handler("ranged_attack", ranged_attack_handler)
bind_handler("melee_engagement", melee_engagement_handler)
bind_handler("suppressive_fire", suppressive_fire_handler)
bind_handler("scout_enemy_positions", scout_enemy_positions_handler)
bind_handler("fortify_combat_zone", fortify_combat_zone_handler)
bind_handler("deploy_archers", deploy_archers_handler)
bind_handler("set_ambush", set_ambush_handler)
bind_handler("counter_attack", counter_attack_handler)


def _resolve_npcs(game_state: GameState, npc_ids: Iterable[str]) -> List[NPC]:
    resolved: List[NPC] = []
    for npc_id in npc_ids or []:
        if not npc_id:
            continue
        npc = game_state.get_npc(str(npc_id))
        if npc:
            resolved.append(npc)
    return resolved


def _apply_engagement_effects(
    game_state: GameState,
    participants: List[NPC],
    casualty_count: int,
    morale_delta: int,
) -> List[Dict[str, Any]]:
    if not participants:
        return []
    ordered = sorted(participants, key=lambda npc: npc.id)
    updates: List[Dict[str, Any]] = []
    injuries = min(len(ordered), max(0, casualty_count))
    for idx, npc in enumerate(ordered):
        morale_change = _distributed_delta(morale_delta, len(ordered), idx)
        if casualty_count > 0:
            health_loss = 12 if idx < injuries else 4
        else:
            health_loss = 2 if idx == 0 else 1
        new_health = max(0, npc.health - health_loss)
        new_morale = max(0, min(100, npc.morale + morale_change))
        new_fatigue = min(100, npc.fatigue + 8)
        updated = game_state.update_npc(
            npc.id,
            health=new_health,
            morale=new_morale,
            fatigue=new_fatigue,
        )
        updates.append(
            {
                "id": updated.id,
                "health": updated.health,
                "morale": updated.morale,
            }
        )
    return updates


def _distributed_delta(total: int, count: int, idx: int) -> int:
    if count <= 0:
        return 0
    if total >= 0:
        base = total // count
        remainder = total % count
        return base + (1 if idx < remainder else 0)
    positive = -total
    base = -(positive // count)
    remainder = positive % count
    return base - (1 if idx < remainder else 0)


def _structure_status(structure: Structure) -> str:
    if structure.integrity <= 0:
        return "breached"
    ratio = structure.integrity / max(1, structure.max_integrity)
    if ratio < 0.3:
        return "critical"
    if ratio < 0.8:
        return "damaged"
    return "stable"


def _serialize_structure(structure: Structure, damage: int) -> Dict[str, Any]:
    return {
        "id": structure.id,
        "integrity": structure.integrity,
        "max_integrity": structure.max_integrity,
        "status": structure.status,
        "damage": damage,
    }
