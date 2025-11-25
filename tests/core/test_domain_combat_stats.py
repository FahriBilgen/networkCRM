from fortress_director.core.domain import NPC, Structure
from fortress_director.core.state_store import GameState


def test_npc_defaults_include_combat_stats():
    npc = NPC(id="npc_a", name="Alpha", role="guard", x=1, y=2)
    assert npc.morale == 50
    assert npc.health == 100
    assert npc.fatigue == 0
    assert npc.skills == {}
    assert npc.status_effects == []


def test_structure_defaults_include_fortification_and_fire_state():
    structure = Structure(id="wall_1", kind="wall", x=0, y=0)
    assert structure.integrity == 100
    assert structure.max_integrity == 100
    assert structure.fortification == 0
    assert structure.on_fire is False


def test_game_state_helper_methods_resolve_domain_entities():
    state = {
        "rng_seed": 7,
        "npc_locations": [
            {
                "id": "npc_a",
                "name": "Alpha",
                "role": "guard",
                "x": 1,
                "y": 1,
                "skills": {"combat": 4},
            },
            {
                "id": "npc_b",
                "name": "Beta",
                "role": "scout",
                "x": 9,
                "y": 9,
            },
        ],
        "structures": {
            "wall_1": {
                "id": "wall_1",
                "kind": "wall",
                "x": 0,
                "y": 0,
                "integrity": 85,
            },
        },
    }
    gs = GameState(state)
    npc = gs.get_npc("npc_a")
    assert npc is not None
    assert npc.skills["combat"] == 4
    struct = gs.get_structure("wall_1")
    assert struct is not None
    assert struct.integrity == 85
    area_npcs = gs.get_npcs_in_area(0, 0, 2, 2)
    assert [n.id for n in area_npcs] == ["npc_a"]
