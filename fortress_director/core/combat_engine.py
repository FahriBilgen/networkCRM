"""Deterministic combat engine used by safe functions."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List

from fortress_director.core.domain import NPC, Structure
from fortress_director.core.state_store import GameState


@dataclass
class CombatOutcome:
    attackers_casualties: int
    defenders_casualties: int
    attackers_morale_delta: int
    defenders_morale_delta: int
    structure_damage: int
    summary: str


def resolve_skirmish(
    game_state: GameState,
    attackers: List[NPC],
    defenders: List[NPC],
    location_structure: Structure | None = None,
) -> CombatOutcome:
    """
    Deterministic, lightweight skirmish resolution:
    - Attack/defense score = skill["combat"] + morale bonus - fatigue penalty
    - Randomness depends only on rng_seed+turn for reproducibility.
    """

    turn_index = _turn_index(game_state)
    rng_seed = int(game_state.rng_seed)
    seed_value = (rng_seed * 97 + turn_index * 53 + len(attackers) * 17 + len(defenders) * 19) & 0xFFFFFFFF
    rng = random.Random(seed_value)
    atk_power = _side_power(attackers)
    def_power = _side_power(defenders)
    if location_structure:
        def_power += max(0, location_structure.fortification) * 0.5
        def_power += location_structure.integrity / 25.0
    total_power = max(1.0, atk_power + def_power)
    ratio = atk_power / total_power
    base_rate = 0.1 + rng.random() * 0.05
    atk_rate = _clamp(base_rate + (0.5 - ratio) * 0.25, 0.05, 0.35)
    def_rate = _clamp(base_rate + (ratio - 0.5) * 0.25, 0.05, 0.35)
    attackers_casualties = _casualties(len(attackers), atk_rate)
    defenders_casualties = _casualties(len(defenders), def_rate)
    morale_swing = int(round((ratio - 0.5) * 10))
    attackers_morale_delta = _clamp_int(morale_swing - attackers_casualties, -20, 10)
    defenders_morale_delta = _clamp_int(-morale_swing - defenders_casualties, -20, 10)
    structure_damage = 0
    if location_structure and ratio > 0.55:
        raw_damage = int(round((ratio - 0.5) * 20 + rng.random() * 3))
        mitigation = max(location_structure.fortification // 2, 0)
        structure_damage = max(0, raw_damage - mitigation)
        structure_damage = min(structure_damage, location_structure.integrity)
        if structure_damage:
            location_structure.integrity = max(
                0, location_structure.integrity - structure_damage
            )
    outcome = _summarize(
        attackers_casualties,
        defenders_casualties,
        structure_damage,
        ratio,
    )
    return CombatOutcome(
        attackers_casualties=attackers_casualties,
        defenders_casualties=defenders_casualties,
        attackers_morale_delta=attackers_morale_delta,
        defenders_morale_delta=defenders_morale_delta,
        structure_damage=structure_damage,
        summary=outcome,
    )


def _side_power(npcs: List[NPC]) -> float:
    if not npcs:
        return 0.0
    total = 0.0
    for npc in npcs:
        skill = int(npc.skills.get("combat", 1))
        morale_bonus = npc.morale // 10
        fatigue_penalty = npc.fatigue // 5
        total += max(1, skill + morale_bonus - fatigue_penalty)
    return max(total, 0.0)


def _casualties(count: int, rate: float) -> int:
    if count <= 0:
        return 0
    estimated = int(math.ceil(max(0.0, count * rate)))
    return max(0, min(count, estimated))


def _turn_index(game_state: GameState) -> int:
    snapshot = game_state.snapshot()
    metrics = snapshot.get("metrics") or {}
    try:
        return int(snapshot.get("turn") or metrics.get("turn") or 0)
    except (TypeError, ValueError):
        return 0


def _summarize(
    atk_losses: int,
    def_losses: int,
    structure_damage: int,
    ratio: float,
) -> str:
    if ratio >= 0.6:
        tide = "Attackers surge forward"
    elif ratio <= 0.4:
        tide = "Defenders hold firm"
    else:
        tide = "Skirmish grinds on"
    parts = [
        tide,
        f"{atk_losses} attackers down",
        f"{def_losses} defenders down",
    ]
    if structure_damage:
        parts.append(f"structure suffers {structure_damage} damage")
    return "; ".join(parts)


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, value))


def _clamp_int(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, value))
