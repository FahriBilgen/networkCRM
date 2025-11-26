"""Passive world simulation applied each turn."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

from fortress_director.core.domain import NPC, Structure
from fortress_director.core.state_store import GameState


def world_tick(game_state: GameState) -> Dict[str, Any]:
    """Advance passive simulation and return a delta suitable for apply_delta."""

    rng = random.Random(_seed(game_state))
    npc_list = list(game_state.as_domain().npcs.values())
    npc_updates, avg_morale, avg_fatigue = _adjust_npcs(game_state, npc_list)
    struct_updates = _decay_structures(game_state, rng)
    food_consumed = _consume_food(game_state, len(npc_list))
    summary = {
        "npc_updates": npc_updates,
        "structure_updates": struct_updates,
        "food_consumed": food_consumed,
        "avg_morale": round(avg_morale, 1) if npc_list else 0,
        "avg_fatigue": round(avg_fatigue, 1) if npc_list else 0,
        "events": [],
    }
    if struct_updates:
        summary["events"].append("Fires gnaw at the ramparts.")
    if food_consumed == 0:
        summary["events"].append("Storerooms are empty; hunger grows.")
    elif food_consumed >= max(1, len(npc_list) // 2):
        summary["events"].append("Food stores drop by {} rations.".format(food_consumed))
    if rng.random() < 0.15:
        summary["events"].append("Wind scatters embers across the courtyard.")
    delta: Dict[str, Any] = {}
    if food_consumed:
        delta["stockpiles"] = {"food": -food_consumed}
    delta["world_tick_summary"] = summary
    return delta


def _seed(game_state: GameState) -> int:
    snapshot = game_state.snapshot()
    metrics = snapshot.get("metrics") or {}
    try:
        turn = int(snapshot.get("turn") or metrics.get("turn") or 0)
    except (TypeError, ValueError):
        turn = 0
    return (int(game_state.rng_seed) * 131 + turn * 17) & 0xFFFFFFFF


def _adjust_npcs(
    game_state: GameState, npcs: List[NPC]
) -> Tuple[List[Dict[str, Any]], float, float]:
    updates: List[Dict[str, Any]] = []
    morale_total = 0.0
    fatigue_total = 0.0
    for npc in npcs:
        fatigue_delta = 1 if npc.fatigue < 100 else 0
        morale_delta = 0
        if npc.morale > 50:
            morale_delta = -1
        elif npc.morale < 50:
            morale_delta = 1
        new_fatigue = min(100, npc.fatigue + fatigue_delta)
        new_morale = max(0, min(100, npc.morale + morale_delta))
        updated = game_state.update_npc(
            npc.id,
            fatigue=new_fatigue,
            morale=new_morale,
        )
        morale_total += updated.morale
        fatigue_total += updated.fatigue
        updates.append(
            {
                "id": updated.id,
                "fatigue_delta": new_fatigue - npc.fatigue,
                "morale_delta": new_morale - npc.morale,
            }
        )
    count = len(npcs) if npcs else 1
    return updates, morale_total / count, fatigue_total / count


def _decay_structures(game_state: GameState, rng: random.Random) -> List[Dict[str, Any]]:
    updates: List[Dict[str, Any]] = []
    structures = list(game_state.as_domain().structures.values())
    for struct in structures:
        if not struct.on_fire:
            continue
        damage = min(struct.integrity, rng.randint(1, 3))
        new_integrity = max(0, struct.integrity - damage)
        updated = game_state.update_structure(
            struct.id,
            integrity=new_integrity,
            status=_structure_status(new_integrity, struct.max_integrity),
            on_fire=new_integrity > 0 and struct.on_fire,
        )
        updates.append(
            {
                "id": updated.id,
                "integrity_delta": -damage,
            }
        )
    return updates


def _consume_food(game_state: GameState, npc_count: int) -> int:
    snapshot = game_state.snapshot()
    stockpiles = snapshot.get("stockpiles") or {}
    food_available = int(stockpiles.get("food", 0) or 0)
    consumption = max(1, npc_count // 2) if npc_count else 0
    return min(consumption, food_available)


def _structure_status(integrity: int, max_integrity: int) -> str:
    if integrity <= 0:
        return "breached"
    ratio = integrity / max(1, max_integrity)
    if ratio < 0.3:
        return "critical"
    if ratio < 0.8:
        return "damaged"
    return "stable"
