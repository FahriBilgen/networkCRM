from fortress_director.core.state_store import GameState
from fortress_director.pipeline.world_tick import world_tick


def test_world_tick_updates_food_fatigue_and_fires():
    state = {
        "rng_seed": 55,
        "npc_locations": [
            {"id": "npc_a", "name": "Guard A", "role": "guard", "x": 1, "y": 2, "fatigue": 10},
            {"id": "npc_b", "name": "Guard B", "role": "guard", "x": 2, "y": 2, "fatigue": 5},
        ],
        "structures": {
            "wall": {
                "id": "wall",
                "kind": "wall",
                "x": 5,
                "y": 5,
                "integrity": 80,
                "max_integrity": 100,
                "on_fire": True,
            }
        },
        "stockpiles": {"food": 20, "wood": 0, "ore": 0},
    }
    game_state = GameState(state)
    delta = world_tick(game_state)
    summary = delta.pop("world_tick_summary")
    game_state.apply_delta(delta)
    assert summary["food_consumed"] >= 1
    assert summary["npc_updates"]
    assert summary["structure_updates"]
    updated_npc = game_state.get_npc("npc_a")
    assert updated_npc is not None and updated_npc.fatigue >= 11
    structure = game_state.get_structure("wall")
    assert structure is not None and structure.integrity < 80
    snapshot = game_state.snapshot()
    assert snapshot["stockpiles"]["food"] < 20
