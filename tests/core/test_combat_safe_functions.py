from fortress_director.core.functions.impl import combat as combat_functions
from fortress_director.core.state_store import GameState


def _build_state() -> dict:
    return {
        "rng_seed": 77,
        "npc_locations": [
            {
                "id": "att_1",
                "name": "Shield One",
                "role": "guard",
                "x": 1,
                "y": 1,
                "skills": {"combat": 6},
                "morale": 70,
            },
            {
                "id": "att_2",
                "name": "Shield Two",
                "role": "guard",
                "x": 2,
                "y": 1,
                "skills": {"combat": 5},
                "morale": 68,
            },
            {
                "id": "def_1",
                "name": "Raider One",
                "role": "raider",
                "x": 5,
                "y": 5,
                "skills": {"combat": 2},
                "morale": 40,
            },
            {
                "id": "def_2",
                "name": "Raider Two",
                "role": "raider",
                "x": 6,
                "y": 5,
                "skills": {"combat": 1},
                "morale": 35,
            },
        ],
        "structures": {
            "gate": {
                "id": "gate",
                "kind": "gate",
                "x": 5,
                "y": 5,
                "integrity": 95,
                "max_integrity": 100,
                "fortification": 1,
            }
        },
    }


def test_melee_engagement_updates_npc_health_and_structure():
    game_state = GameState(_build_state())
    response = combat_functions.melee_engagement_handler(
        game_state,
        attacker_ids=["att_1", "att_2"],
        defender_ids=["def_1", "def_2"],
        structure_id="gate",
    )
    attacker = game_state.get_npc("att_1")
    defender = game_state.get_npc("def_1")
    assert attacker is not None and defender is not None
    assert attacker.health < 100 or defender.health < 100
    structure = game_state.get_structure("gate")
    assert structure is not None and structure.integrity < 95
    combat_effects = response["effects"]["combat"]["outcome"]
    assert combat_effects["attackers_casualties"] >= 0
    assert combat_effects["defenders_casualties"] >= 0
