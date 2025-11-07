from __future__ import annotations

from copy import deepcopy

from fortress_director.orchestrator.orchestrator import (
    DEFAULT_WORLD_STATE,
    Orchestrator,
)


def _fresh_state() -> dict:
    return deepcopy(DEFAULT_WORLD_STATE)


def test_finale_cards_victory_profile() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _fresh_state()
    metrics = state["metrics"]
    metrics.update(
        {
            "morale": 72,
            "order": 68,
            "resources": 55,
            "glitch": 10,
            "corruption": 5,
            "major_events_triggered": 3,
            "major_event_last_turn": 9,
        }
    )

    cards = orchestrator._build_finale_cards(state, {"status": "win", "reason": "siege_broken"})

    assert cards[0]["ending"] == "victory"
    assert cards[0]["title"] == "Citadel Holds"
    assert cards[1]["id"] == "cost"
    assert cards[2]["id"] == "legacy"


def test_finale_cards_defeat_profile() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _fresh_state()
    metrics = state["metrics"]
    metrics.update(
        {
            "morale": 20,
            "order": 25,
            "resources": 18,
            "glitch": 40,
            "corruption": 15,
        }
    )

    cards = orchestrator._build_finale_cards(state, {"status": "loss", "reason": "walls_breached"})

    assert cards[0]["ending"] == "defeat"
    assert "Walls Breached" in cards[0]["title"]
    assert cards[1]["title"] in {"Empty Stores", "System Strain", "Frayed Loyalties"}


def test_finale_cards_pyrrhic_profile_due_to_glitch() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _fresh_state()
    metrics = state["metrics"]
    metrics.update(
        {
            "morale": 58,
            "order": 60,
            "resources": 45,
            "glitch": 70,
            "corruption": 12,
            "major_events_triggered": 2,
        }
    )

    cards = orchestrator._build_finale_cards(state, {"status": "win", "reason": "but_at_a_cost"})

    assert cards[0]["ending"] == "pyrrhic"
    assert cards[1]["title"] == "System Strain"
