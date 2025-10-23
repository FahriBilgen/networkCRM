from __future__ import annotations

from fortress_director.orchestrator.orchestrator import Orchestrator


def _make_orchestrator() -> Orchestrator:
    return Orchestrator.__new__(Orchestrator)


def test_fallback_reaction_infers_name_and_limits_speech() -> None:
    orchestrator = _make_orchestrator()
    state = {"character_summary": "Boris calculates every move."}
    choice = {"action_type": "talk"}

    reaction = orchestrator._build_fallback_reaction(state, choice)

    assert reaction["name"] == "Boris"
    assert reaction["intent"] == "defend"
    assert reaction["action"] == "hold_position"
    assert len(reaction["speech"]) <= 200
    assert reaction["effects"] == {}


def test_infer_primary_npc_name_defaults_to_rhea() -> None:
    orchestrator = _make_orchestrator()
    state = {"character_summary": ""}

    assert orchestrator._infer_primary_npc_name(state) == "Rhea"


def test_inject_major_event_effect_adds_flag_and_status() -> None:
    orchestrator = _make_orchestrator()
    state = {"flags": ["mystery_figure"]}
    event_output = {"major_event": True}
    reaction = {
        "name": "Rhea",
        "intent": "listen",
        "action": "attention",
        "speech": "Holding the line.",
        "effects": {},
    }

    effect = orchestrator._inject_major_event_effect(
        state,
        event_output,
        [reaction],
    )

    assert effect is not None
    assert effect["applied_flag"] == "major_mystery_investigation"
    applied_effects = reaction["effects"]
    assert "major_mystery_investigation" in applied_effects["flag_set"]
    assert applied_effects["status_change"]["status"] == "tense_watch"
    assert applied_effects["status_change"]["duration"] == 3


def test_inject_major_event_effect_noop_when_not_major() -> None:
    orchestrator = _make_orchestrator()
    state = {"flags": []}
    event_output = {"major_event": False}
    reaction = {
        "name": "Rhea",
        "intent": "listen",
        "action": "attention",
        "speech": "Holding the line.",
        "effects": {},
    }

    effect = orchestrator._inject_major_event_effect(
        state,
        event_output,
        [reaction],
    )

    assert effect is None
    assert reaction["effects"] == {}
