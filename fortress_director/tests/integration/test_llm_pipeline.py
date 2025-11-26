import os

import pytest

from fortress_director.core.state_store import GameState
from fortress_director.pipeline.turn_manager import run_turn
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file

pytestmark = pytest.mark.integration
RUN_REAL_LLM = os.environ.get("FORTRESS_RUN_LLM_TESTS") == "1"


@pytest.mark.skipif(
    not RUN_REAL_LLM,
    reason="Set FORTRESS_RUN_LLM_TESTS=1 to enable real LLM integration tests.",
)
def test_full_turn_with_llm() -> None:
    """Run one turn with real LLM calls."""

    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    result = run_turn(GameState(), player_choice={"id": "option_1"}, theme=theme)
    assert result.narrative
    assert len(result.executed_actions) > 0
    assert result.player_options


@pytest.mark.skipif(
    not RUN_REAL_LLM,
    reason="Set FORTRESS_RUN_LLM_TESTS=1 to enable real LLM integration tests.",
)
def test_golden_path_with_llm() -> None:
    """Run multiple turns to ensure stability metrics remain present."""

    game_state = GameState()
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    for turn in range(7):
        _ = run_turn(
            game_state,
            player_choice={"id": f"option_{(turn % 3) + 1}"},
            theme=theme,
        )
        projection = game_state.get_projected_state()
        assert "stability" in projection.get("world", {})
