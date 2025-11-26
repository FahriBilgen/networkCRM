from copy import deepcopy
from typing import Any, Dict

from fortress_director.core.state_store import DEFAULT_SESSION_STATE, GameState


def test_game_state_snapshot_isolated_from_mutation() -> None:
    game_state = GameState()
    snap = game_state.snapshot()
    snap["world"]["stability"] = 0
    assert (
        game_state.snapshot()["world"]["stability"]
        == DEFAULT_SESSION_STATE["world"]["stability"]
    )


def test_game_state_apply_delta_and_projection() -> None:
    game_state = GameState()
    projected = game_state.get_projected_state()
    assert {"turn", "world", "metrics", "recent_events"}.issubset(projected)
    assert len(projected["recent_events"]) <= 5

    delta = {"turn": 1, "world": {"stability": 2}, "metrics": {"morale": -3}}
    updated = game_state.apply_delta(delta)
    assert updated["turn"] == DEFAULT_SESSION_STATE["turn"] + 1
    assert (
        updated["world"]["stability"] == DEFAULT_SESSION_STATE["world"]["stability"] + 2
    )
    assert (
        updated["metrics"]["morale"] == DEFAULT_SESSION_STATE["metrics"]["morale"] - 3
    )


def test_game_state_compute_state_delta() -> None:
    before: Dict[str, Any] = {
        "metrics": {"order": 10, "morale": 8},
        "flags": ["calm", "watchful"],
        "log": ["Quiet watch."],
    }
    after = deepcopy(before)
    after["metrics"]["order"] = 13
    after["metrics"]["morale"] = 6
    after["flags"] = ["calm", "alert"]
    after["log"].append("Skirmish erupts near the gate.")
    delta = GameState.compute_state_delta(before, after)
    assert delta["metrics"]["order"] == 3
    assert delta["metrics"]["morale"] == -2
    assert delta["flags_added"] == ["alert"]
    assert delta["flags_removed"] == ["watchful"]
    assert "Skirmish erupts near the gate." in delta["recent_events"]
