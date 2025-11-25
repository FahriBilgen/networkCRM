from fortress_director.core.combat_engine import resolve_skirmish
from fortress_director.core.domain import NPC, Structure
from fortress_director.core.state_store import GameState


def _make_npc(idx: str, combat: int, morale: int = 60, fatigue: int = 0) -> NPC:
    return NPC(
        id=f"npc_{idx}",
        name=f"NPC {idx}",
        role="soldier",
        x=0,
        y=0,
        skills={"combat": combat},
        morale=morale,
        fatigue=fatigue,
    )


def test_stronger_attackers_inflict_more_casualties():
    game_state = GameState({"turn": 3, "rng_seed": 42})
    attackers = [_make_npc("a1", 6), _make_npc("a2", 5)]
    defenders = [_make_npc("d1", 2, morale=45), _make_npc("d2", 1, morale=40)]
    outcome = resolve_skirmish(game_state, attackers, defenders)
    assert outcome.defenders_casualties >= outcome.attackers_casualties
    assert outcome.defenders_morale_delta <= 0


def test_structure_takes_damage_when_attackers_push_through():
    game_state = GameState({"turn": 4, "rng_seed": 21})
    attackers = [_make_npc("a1", 7, morale=70), _make_npc("a2", 6, morale=65)]
    defenders = [_make_npc("d1", 2, morale=55)]
    structure = Structure(id="gate", kind="gate", x=0, y=0, integrity=90, fortification=1)
    outcome = resolve_skirmish(game_state, attackers, defenders, structure)
    assert outcome.structure_damage > 0
    assert structure.integrity == 90 - outcome.structure_damage


def test_skirmish_is_deterministic_for_same_state():
    attackers = [_make_npc("a1", 4)]
    defenders = [_make_npc("d1", 3)]
    gs_a = GameState({"turn": 5, "rng_seed": 11})
    gs_b = GameState({"turn": 5, "rng_seed": 11})
    outcome_a = resolve_skirmish(gs_a, attackers, defenders)
    outcome_b = resolve_skirmish(gs_b, attackers, defenders)
    assert outcome_a == outcome_b
