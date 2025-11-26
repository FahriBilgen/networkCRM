from typing import List, get_args, get_origin, get_type_hints

from fortress_director.themes.schema import (
    ThemeConfig,
    ThemeEndingSpec,
    ThemeMapSpec,
    ThemeNpcSpec,
)


def test_theme_config_dataclasses_constructible():
    map_spec = ThemeMapSpec(width=4, height=4, layout=[["wall"] * 4 for _ in range(4)])
    npc = ThemeNpcSpec(
        id="hero",
        name="Test Hero",
        role="commander",
        x=1,
        y=2,
        tags=["leader"],
    )
    ending = ThemeEndingSpec(
        id="victory",
        label="Victory",
        conditions={"wall_integrity_min": 50},
    )
    config = ThemeConfig(
        id="demo",
        label="Demo Theme",
        description="A sample theme for unit tests.",
        map=map_spec,
        npcs=[npc],
        initial_metrics={"turn": 1, "morale": 55},
        event_graph_file="event_graph.json",
        safe_function_overrides={"reinforce_wall": {"gas_cost": 2}},
        endings=[ending],
    )
    assert config.map.width == 4
    assert config.npcs[0].tags == ["leader"]
    assert config.endings[0].conditions["wall_integrity_min"] == 50


def test_theme_config_field_annotations():
    annotations = get_type_hints(ThemeConfig)
    assert annotations["map"] is ThemeMapSpec
    assert get_origin(annotations["npcs"]) in (list, List)
    npc_args = get_args(annotations["npcs"])
    assert ThemeNpcSpec in npc_args
    endings_origin = get_origin(annotations["endings"])
    assert endings_origin in (list, List)
    endings_args = get_args(annotations["endings"])
    assert ThemeEndingSpec in endings_args
