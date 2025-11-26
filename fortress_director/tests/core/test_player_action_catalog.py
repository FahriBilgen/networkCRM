from fortress_director.core import player_action_catalog


def test_load_actions_returns_list():
    actions = player_action_catalog.load_actions()
    assert isinstance(actions, list)
    assert any(a.get("id") == "repair_wall" for a in actions)


def test_get_action_by_id():
    entry = player_action_catalog.get_action_by_id("move_npc")
    assert entry is not None
    assert entry["safe_function"] == "move_npc"




def test_load_actions_returns_catalog() -> None:
    actions = player_action_catalog.load_actions()
    assert actions
    first = actions[0]
    assert first["id"]
    assert first["safe_function"]


def test_get_action_by_id_finds_entry() -> None:
    entry = player_action_catalog.get_action_by_id("move_npc")
    assert entry is not None
    assert entry["safe_function"] == "move_npc"
    assert "x" in entry["requires"]
