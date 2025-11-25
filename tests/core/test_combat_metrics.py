from fortress_director.core.functions.impl import combat as combat_functions
from fortress_director.core.state_store import GameState


def _state_for_metrics() -> dict:
    return {
        "rng_seed": 91,
        "npc_locations": [
            {
                "id": "att_1",
                "name": "Shield One",
                "role": "guard",
                "x": 1,
                "y": 1,
                "skills": {"combat": 5},
                "morale": 65,
            },
            {
                "id": "att_2",
                "name": "Shield Two",
                "role": "guard",
                "x": 2,
                "y": 1,
                "skills": {"combat": 5},
                "morale": 63,
            },
            {
                "id": "att_3",
                "name": "Shield Three",
                "role": "guard",
                "x": 3,
                "y": 1,
                "skills": {"combat": 4},
                "morale": 62,
            },
            {
                "id": "def_1",
                "name": "Raider One",
                "role": "raider",
                "x": 6,
                "y": 5,
                "skills": {"combat": 2},
                "morale": 45,
            },
            {
                "id": "def_2",
                "name": "Raider Two",
                "role": "raider",
                "x": 7,
                "y": 5,
                "skills": {"combat": 2},
                "morale": 44,
            },
            {
                "id": "def_3",
                "name": "Raider Three",
                "role": "raider",
                "x": 8,
                "y": 5,
                "skills": {"combat": 1},
                "morale": 42,
            },
        ],
    }


def test_combat_metrics_accumulate_across_skirmishes():
    game_state = GameState(_state_for_metrics())
    for _ in range(2):
        combat_functions.melee_engagement_handler(
            game_state,
            attacker_ids=["att_1", "att_2", "att_3"],
            defender_ids=["def_1", "def_2", "def_3"],
        )
    combat_metrics = game_state.snapshot()["metrics"]["combat"]
    assert combat_metrics["total_skirmishes"] == 2
    assert combat_metrics["total_casualties_friendly"] > 0
    assert combat_metrics["total_casualties_enemy"] > 0
