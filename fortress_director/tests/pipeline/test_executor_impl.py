from __future__ import annotations

from fortress_director.core.state_store import GameState
from fortress_director.pipeline import function_executor


def _game_state_payload() -> dict:
    return {
        "turn": 0,
        "world": {"stability": 40, "resources": 70},
        "metrics": {
            "order": 10,
            "morale": 50,
            "resources": 30,
            "knowledge": 5,
            "glitch": 0,
            "wall_integrity": 40,
        },
        "npc_locations": [
            {"id": "ila", "name": "Scout Ila", "role": "scout", "x": 1, "y": 1},
        ],
        "structures": {
            "wall": {
                "id": "wall",
                "kind": "wall",
                "integrity": 50,
                "max_integrity": 100,
            },
        },
        "map_event_markers": [],
        "log": [],
    }


def test_executor_moves_npc_and_updates_positions() -> None:
    game_state = GameState(_game_state_payload())
    plan = [
        {"function": "move_npc", "args": {"npc_id": "ila", "x": 4, "y": 5}},
    ]
    result = function_executor.apply_actions(game_state, plan)
    world_state = result["world_state"]
    executed = result["executed_actions"]
    state_delta = result["state_delta"]
    assert world_state["npc_locations"][0]["x"] == 4
    assert world_state["npc_locations"][0]["y"] == 5
    assert executed[0]["function"] == "move_npc"
    assert state_delta["npc_positions"]["ila"]["x"] == 4
    assert state_delta["turn_advanced"] is True


def test_executor_reinforces_wall_and_reports_integrity() -> None:
    game_state = GameState(_game_state_payload())
    plan = [
        {
            "function": "reinforce_wall",
            "args": {"structure_id": "wall", "amount": 10, "material": "stone"},
        }
    ]
    result = function_executor.apply_actions(game_state, plan)
    world_state = result["world_state"]
    state_delta = result["state_delta"]
    assert world_state["structures"]["wall"]["integrity"] > 50
    assert "wall" in state_delta["wall_integrity"]


def test_executor_handles_event_markers_and_metrics() -> None:
    game_state = GameState(_game_state_payload())
    plan = [
        {
            "function": "spawn_event_marker",
            "args": {"marker_id": "flare", "x": 2, "y": 2, "severity": 2},
        },
        {
            "function": "adjust_metric",
            "args": {"metric": "morale", "delta": 2},
        },
    ]
    result = function_executor.apply_actions(game_state, plan)
    world_state = result["world_state"]
    state_delta = result["state_delta"]
    assert len(world_state["map_event_markers"]) == 1
    assert state_delta["event_markers"][0]["id"] == "flare"
    assert state_delta["morale_change"] == 2
