from fortress_director.core import player_action_catalog, player_action_router


def test_router_maps_required_calls():
    catalog_entry = player_action_catalog.get_action_by_id("repair_wall")
    params = {"structure_id": "western_wall", "amount": 2}
    routed = player_action_router.route_player_action(
        "repair_wall", params, catalog_entry
    )
    assert "player_intent" in routed
    rc = routed.get("required_calls")
    assert isinstance(rc, list) and rc
    assert rc[0]["function"] == "reinforce_wall"
    assert rc[0]["args"]["structure_id"] == "western_wall"




def test_route_player_action_maps_required_calls() -> None:
    entry = player_action_catalog.get_action_by_id("repair_wall")
    assert entry is not None
    context = player_action_router.route_player_action(
        "repair_wall",
        {"structure_id": "gate_1", "amount": 1},
        entry,
    )
    assert context["player_intent"] == "repair wall gate_1"
    required = context["required_calls"][0]
    assert required["function"] == "reinforce_wall"
    assert required["args"]["structure_id"] == "gate_1"
