from __future__ import annotations

from fortress_director.agents.event_agent import EventAgent
from fortress_director.llm.offline_client import OfflineOllamaClient


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


def test_event_agent_diversity_pool() -> None:
    """Test that EventAgent selects event_type from diversity pool."""
    agent = EventAgent(client=OfflineOllamaClient(agent_key="event"))
    variables = {"day": 1, "world_context": "Test context"}

    # Mock the run method to capture variables passed to it
    original_run = agent.run
    captured_vars = {}

    def mock_run(self, variables):
        captured_vars.update(variables)
        return {"scene": "Test scene", "options": []}

    agent.run = mock_run.__get__(agent, EventAgent)

    try:
        result = agent.generate(variables)
        # Check that event_type was added from pool
        assert "event_type" in captured_vars
        assert captured_vars["event_type"] in [
            "siege_incident",
            "internal_conflict",
            "resource_scarcity",
            "diplomatic_encounter",
            "mystical_occurrence",
            "environmental_hazard",
            "personal_drama",
            "strategic_opportunity",
        ]
        assert "diversity_hint" in captured_vars
        assert captured_vars["event_type"] in captured_vars["diversity_hint"]
    finally:
        agent.run = original_run
