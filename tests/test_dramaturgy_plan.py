from __future__ import annotations

from copy import deepcopy

from fortress_director.orchestrator.orchestrator import (
    DEFAULT_WORLD_STATE,
    Orchestrator,
)


def _base_state(turn: int) -> dict:
    state = deepcopy(DEFAULT_WORLD_STATE)
    state["turn"] = turn
    state["flags"] = []
    return state


def test_dramaturgy_prologue_defaults() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _base_state(1)

    profile = orchestrator._update_dramaturgy_state(
        state, current_turn=1, major_events=0, last_major_turn=None
    )

    assert profile["stage"] == "prologue"
    assert profile["risk_delta"] == 0
    assert profile["allow_major"] is False
    assert "stage_prologue" in state["flags"]


def test_dramaturgy_escalation_allows_major_events() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _base_state(6)

    profile = orchestrator._update_dramaturgy_state(
        state, current_turn=6, major_events=1, last_major_turn=None
    )

    assert profile["stage"] == "escalation"
    assert profile["allow_major"] is True
    assert profile["force_major"] is True
    assert profile["risk_delta"] >= 1


def test_dramaturgy_crisis_sets_finale_hint() -> None:
    orchestrator = Orchestrator.__new__(Orchestrator)
    state = _base_state(10)

    profile = orchestrator._update_dramaturgy_state(
        state, current_turn=10, major_events=2, last_major_turn=7
    )

    assert profile["stage"] == "crisis"
    assert profile["finale_hint"] == "prepare_finale"
    assert "stage_crisis" in state["flags"]
