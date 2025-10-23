from __future__ import annotations

from fortress_director.agents.character_agent import (
    CharacterAgent,
    MAX_SPEECH_LENGTH,
)


def _long_text(prefix: str, length: int) -> str:
    base = (prefix or "x") * (length // max(len(prefix), 1))
    remainder = prefix[: length - len(base)]
    return (base + remainder)[:length]


def test_normalise_entries_sanitises_invalid_data() -> None:
    agent = CharacterAgent()
    noisy_entry = {
        "name": 123,
        "intent": None,
        "action": "scan_horizon",
        "speech": _long_text(
            "mist",
            MAX_SPEECH_LENGTH + 140,
        ),
        "effects": {
            "trust_delta": 4,
            "flag_set": ["", "watch", 99],
            "item_change": {
                "item": "oil lamp",
                "delta": 0,
                "target": "player",
            },
            "status_change": {
                "target": "",
                "status": "alert",
                "duration": -5,
            },
        },
    }
    junk_entry = "not-a-dict"

    results = agent._normalise_entries([noisy_entry, junk_entry])

    assert len(results) == 1
    entry = results[0]
    assert entry["name"] == "123"
    assert entry["intent"] == ""
    assert entry["speech"].startswith("mist")
    assert len(entry["speech"]) == MAX_SPEECH_LENGTH

    effects = entry["effects"]
    assert "trust_delta" not in effects
    assert "flag_set" in effects
    assert effects["flag_set"] == ["watch", "99"]
    assert "item_change" not in effects
    assert "status_change" not in effects


def test_normalise_entries_preserves_valid_effects() -> None:
    agent = CharacterAgent()
    valid_entry = {
        "name": "Rhea",
        "intent": "support",
        "action": "brace",
        "speech": "Holding the line.",
        "effects": {
            "trust_delta": 1,
            "item_change": {
                "item": "arrow",
                "delta": -1,
                "target": "player",
            },
            "status_change": {
                "target": "Rhea",
                "status": "focused",
                "duration": 2,
            },
        },
    }

    results = agent._normalise_entries([valid_entry])
    assert len(results) == 1

    effects = results[0]["effects"]
    assert effects["trust_delta"] == 1
    assert effects["item_change"] == {
        "item": "arrow",
        "delta": -1,
        "target": "player",
    }
    assert effects["status_change"] == {
        "target": "Rhea",
        "status": "focused",
        "duration": 2,
    }
