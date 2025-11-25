from __future__ import annotations

from fortress_director.narrative.final_paths import determine_final_path


def _base_state() -> dict:
    return {
        "metrics": {"morale": 50, "corruption": 10},
        "npc_locations": [],
        "world": {"stability": 50},
    }


def test_victory_defense_selected_when_morale_high() -> None:
    state = _base_state()
    state["metrics"]["morale"] = 75
    path = determine_final_path(state, metrics=state["metrics"], threat_score=20)
    assert path.id == "victory_defense"


def test_evacuation_success_when_population_survives() -> None:
    state = _base_state()
    state["metrics"]["morale"] = 55
    state["npc_locations"] = [
        {"id": "npc_1", "status": "alive"},
        {"id": "npc_2", "status": "alive"},
        {"id": "npc_3", "status": "dead", "role": "captain"},
        {"id": "npc_4", "status": "alive"},
    ]
    path = determine_final_path(state, metrics=state["metrics"], threat_score=45)
    assert path.id == "evacuation_success"


def test_heroic_last_stand_requires_high_threat_and_losses() -> None:
    state = _base_state()
    state["npc_locations"] = [
        {"id": "npc_1", "status": "dead", "role": "captain"},
        {"id": "npc_2", "status": "fallen", "role": "commander"},
        {"id": "npc_3", "status": "dead", "role": "seer"},
    ]
    path = determine_final_path(state, metrics=state["metrics"], threat_score=95)
    assert path.id == "heroic_last_stand"


def test_collapse_failure_when_threat_extreme_and_morale_low() -> None:
    state = _base_state()
    state["metrics"]["morale"] = 20
    path = determine_final_path(state, metrics=state["metrics"], threat_score=96)
    assert path.id == "collapse_failure"


def test_unknown_anomaly_when_corruption_spikes() -> None:
    state = _base_state()
    state["metrics"]["corruption"] = 80
    state["npc_locations"] = [
        {"status": "dead"},
        {"status": "dead"},
        {"status": "alive"},
    ]
    path = determine_final_path(state, metrics=state["metrics"], threat_score=10)
    assert path.id == "unknown_anomaly"


def test_betrayal_ending_when_alignment_negative() -> None:
    state = _base_state()
    state["metrics"]["leadership_alignment"] = -35
    state["npc_locations"] = [
        {"status": "dead"},
        {"status": "dead"},
        {"status": "alive"},
    ]
    path = determine_final_path(state, metrics=state["metrics"], threat_score=55)
    assert path.id == "betrayal_ending"


def test_default_path_is_bittersweet_survival() -> None:
    state = _base_state()
    state["npc_locations"] = [
        {"status": "dead"},
        {"status": "dead"},
        {"status": "dead"},
        {"status": "alive"},
    ]
    path = determine_final_path(state, metrics=state["metrics"], threat_score=40)
    assert path.id == "bittersweet_survival"
