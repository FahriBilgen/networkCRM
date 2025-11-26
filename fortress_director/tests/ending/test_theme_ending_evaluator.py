from fortress_director.core.state_store import GameState
from fortress_director.ending.evaluator import evaluate_ending
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file


def _load_theme(theme_id: str):
    return load_theme_from_file(BUILTIN_THEMES[theme_id])


def test_theme_ending_evaluator_handles_siege_default() -> None:
    theme = _load_theme("siege_default")
    state = GameState.from_theme_config(theme)
    assert evaluate_ending(state, theme) == "victory"


def test_theme_ending_evaluator_handles_orbital_outpost_variants() -> None:
    theme = _load_theme("orbital_outpost")
    state = GameState.from_theme_config(theme)
    snapshot = state.snapshot()
    snapshot["metrics"]["wall_integrity"] = 10
    snapshot["metrics"]["morale"] = 5
    snapshot["metrics"]["threat"] = 90
    snapshot["metrics"]["resources"] = 10
    state.replace(snapshot)
    assert evaluate_ending(state, theme) == "station_lost"
