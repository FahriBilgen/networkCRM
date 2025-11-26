from fortress_director.engine.api import FortressDirectorEngine
from fortress_director.llm.runtime_mode import set_llm_enabled

set_llm_enabled(False)


def test_engine_reset_initializes_theme_state() -> None:
    engine = FortressDirectorEngine("siege_default")
    snapshot = engine.get_state_snapshot()
    assert snapshot["theme"]["id"] == "siege_default"
    assert snapshot["map"]["width"] == 8
    assert snapshot["npc_positions"]

    updated = engine.reset("orbital_outpost")
    assert updated["theme"]["id"] == "orbital_outpost"
    assert updated["theme"]["label"] == "Orbital Outpost"


def test_engine_run_turn_returns_turn_delta() -> None:
    engine = FortressDirectorEngine("orbital_outpost")
    delta = engine.run_turn()
    assert delta["theme_id"] == "orbital_outpost"
    assert isinstance(delta["npc_positions"], dict)
    assert isinstance(delta["structures"], dict)
    assert isinstance(delta["markers"], list)
    assert "atmosphere" in delta
    assert isinstance(delta["suggested_events_for_host"], list)
    assert "state_delta" in delta


def test_engine_external_events_are_ingested() -> None:
    engine = FortressDirectorEngine("siege_default")
    engine.inject_external_event({"type": "battle_started", "label": "Outer gate"})

    snapshot = engine.get_state_snapshot()
    assert snapshot["external_events"]
    assert snapshot["external_events"][-1]["type"] == "battle_started"

    delta = engine.run_turn()
    assert delta["ingested_external_events"]
    assert delta["ingested_external_events"][0]["type"] == "battle_started"

    follow_up = engine.run_turn()
    assert follow_up["ingested_external_events"] == []
