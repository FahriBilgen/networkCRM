from __future__ import annotations

from fortress_director.core.state_store import GameState


def test_game_state_defaults_expose_game_over_flags() -> None:
    state = GameState()
    assert state.game_over is False
    assert state.ending_id is None

    snapshot = state.snapshot()
    assert snapshot["game_over"] is False
    assert snapshot["ending_id"] is None
