import pytest

from fortress_director.core import player_action_validator
from fortress_director.core.state_store import GameState


def test_missing_param_raises():
    gs = GameState()
    try:
        player_action_validator.validate_player_action(
            "move_npc", {"npc_id": "scout_ila", "x": 2}, gs
        )
        assert False, "expected ValueError for missing y"
    except ValueError as exc:
        assert "missing parameter: y" in str(exc)


def test_npc_not_found():
    gs = GameState()
    try:
        player_action_validator.validate_player_action(
            "assign_patrol", {"npc_id": "nope"}, gs
        )
        assert False, "expected ValueError for npc not found"
    except ValueError as exc:
        assert "npc not found" in str(exc)


def test_structure_not_found():
    gs = GameState()
    try:
        player_action_validator.validate_player_action(
            "repair_wall", {"structure_id": "missing_wall"}, gs
        )
        assert False, "expected ValueError for structure not found"
    except ValueError as exc:
        assert "structure not found" in str(exc)


def test_valid_action_succeeds():
    gs = GameState()
    params = {"structure_id": "western_wall"}
    out = player_action_validator.validate_player_action("repair_wall", params, gs)
    assert out["structure_id"] == "western_wall"

def test_validator_rejects_missing_param() -> None:
    game_state = GameState()
    with pytest.raises(ValueError, match="missing parameter: npc_id"):
        player_action_validator.validate_player_action(
            "move_npc", {"x": 1, "y": 2}, game_state
        )


def test_validator_rejects_unknown_npc() -> None:
    game_state = GameState()
    with pytest.raises(ValueError, match="npc not found"):
        player_action_validator.validate_player_action(
            "move_npc",
            {"npc_id": "ghost", "x": 1, "y": 2},
            game_state,
        )


def test_validator_accepts_valid_payload() -> None:
    game_state = GameState()
    params = player_action_validator.validate_player_action(
        "move_npc",
        {"npc_id": "scout_ila", "x": "4", "y": 3},
        game_state,
    )
    assert params["npc_id"] == "scout_ila"
    assert params["x"] == 4
    assert params["y"] == 3
