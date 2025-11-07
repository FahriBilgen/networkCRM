from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from fortress_director.orchestrator.orchestrator import DEFAULT_WORLD_STATE
from fortress_director.utils.theme_loader import (
    build_world_state_for_theme,
    load_theme_package,
)


def test_load_siege_theme_prompts_and_assets() -> None:
    theme = load_theme_package("siege_default")
    assert theme.id == "siege_default"
    assert theme.prompt_paths["event"].name == "event_prompt.txt"
    assert theme.assets["npc_roster"][0]["id"] == "rhea"


def test_load_scifi_theme_inherits_and_overrides() -> None:
    theme = load_theme_package("orbital_frontier")
    assert theme.prompt_paths["event"].as_posix().endswith(
        "themes/scifi/prompts/event_prompt.txt"
    )
    world = build_world_state_for_theme(theme, deepcopy(DEFAULT_WORLD_STATE))
    assert world["player"]["name"] == "Station Warden"
    assert world["theme_id"] == "orbital_frontier"
