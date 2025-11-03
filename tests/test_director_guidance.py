from __future__ import annotations

from fortress_director.orchestrator.orchestrator import Orchestrator


def test_apply_director_guidance_updates_state_flags_and_budget() -> None:
    snapshot = {
        "turn": 5,
        "flags": ["existing_flag", "force_major_event"],
        "_director_guidance": {"pacing": "steady"},
    }
    payload = {
        "pacing": "accelerate",
        "risk_budget": 4,
        "major_event": "delay",
        "flags_to_add": ["new_flag", "existing_flag"],
        "flags_to_remove": ["force_major_event"],
        "notes": "Escalate tension while stalling majors.",
    }

    risk, allow_major = Orchestrator._apply_director_guidance(
        snapshot,
        payload,
        base_risk_budget=1,
        allow_major=True,
    )

    assert risk == 4
    assert allow_major is False
    assert snapshot["flags"] == ["existing_flag", "new_flag"]

    guidance = snapshot.get("_director_guidance", {})
    assert guidance.get("pacing") == "accelerate"
    assert guidance.get("risk_budget") == 4
    assert guidance.get("major_event") == "delay"
    assert guidance.get("flags_to_add") == ["new_flag"]
    assert guidance.get("flags_to_remove") == ["force_major_event"]
    notes = snapshot.get("_director_notes", [])
    assert notes and notes[-1]["note"].startswith("Escalate tension")


def test_apply_director_guidance_handles_invalid_payload() -> None:
    snapshot = {"turn": 3, "flags": []}

    risk, allow_major = Orchestrator._apply_director_guidance(
        snapshot,
        payload="not-a-dict",  # type: ignore[arg-type]
        base_risk_budget=2,
        allow_major=False,
    )

    assert risk == 2
    assert allow_major is False
    guidance = snapshot.get("_director_guidance", {})
    assert guidance.get("risk_budget") == 2
    assert guidance.get("major_event") == "delay"
    assert guidance.get("pacing") == "steady"
