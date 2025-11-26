import pytest

from fortress_director.themes.loader import (
    BUILTIN_THEMES,
    ThemeRegistry,
    load_builtin_themes,
    load_theme_from_file,
)
from fortress_director.themes.schema import ThemeConfig


def test_builtin_theme_files_parse():
    for theme_id, path in BUILTIN_THEMES.items():
        config = load_theme_from_file(path)
        assert isinstance(config, ThemeConfig)
        assert config.id == theme_id
        assert config.map.width > 0
        assert config.npcs, "Expected at least one NPC per theme"
        assert config.endings, "Expected at least one ending per theme"


def test_registry_register_and_get():
    registry = ThemeRegistry()
    for path in BUILTIN_THEMES.values():
        registry.register(load_theme_from_file(path))
    siege = registry.get("siege_default")
    assert siege.label == "Siege of Lornhaven"
    assert "siege_default" in registry.list_ids()


def test_load_builtin_themes_returns_registry():
    registry = load_builtin_themes()
    assert sorted(registry.list_ids()) == sorted(BUILTIN_THEMES.keys())
    with pytest.raises(KeyError):
        registry.get("nonexistent_theme")
