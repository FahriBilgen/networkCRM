from __future__ import annotations

from fortress_director.agents.event_agent import EventAgent


def test_event_agent_normalises_options() -> None:
    agent = EventAgent()
    raw = {
        "scene": None,
        "options": [
            {"id": "", "text": "", "action_type": ""},
            "invalid",
        ],
        "major_event": "no",
    }

    normalised = agent._normalise_event(raw)

    options = normalised["options"]
    assert len(options) == 1
    option = options[0]
    assert option["id"] == "opt_1"
    assert option["text"] == "Unclear option"
    assert option["action_type"] == "talk"
    assert normalised["scene"] == ""
    assert normalised["major_event"] is False
