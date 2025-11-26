from fortress_director.core.state_store import GameState
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file


def _load_theme(theme_id: str):
    return load_theme_from_file(BUILTIN_THEMES[theme_id])


def test_game_state_from_theme_config_sets_map_and_metrics() -> None:
    theme = _load_theme("siege_default")
    game_state = GameState.from_theme_config(theme)
    snapshot = game_state.snapshot()

    assert snapshot["map"]["width"] == theme.map.width
    assert snapshot["map"]["layout"][0][0] == theme.map.layout[0][0]
    assert len(snapshot["npc_locations"]) == len(theme.npcs)
    assert snapshot["metrics"]["morale"] == theme.initial_metrics["morale"]
    assert snapshot["metrics"]["npc_count"] == len(theme.npcs)
    assert snapshot["theme_id"] == theme.id
    assert snapshot["theme"]["endings"][0]["id"] == theme.endings[0].id
