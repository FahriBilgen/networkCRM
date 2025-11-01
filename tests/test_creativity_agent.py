import pytest
from unittest.mock import patch
from fortress_director.agents.creativity_agent import CreativityAgent, MOTIF_TABLE


class DummyClient:
    def __init__(self, response=None):
        self.response = response or "Novel prompt!"

    def generate(self, **kwargs):
        return {"response": self.response}


def test_motif_injection_every_3rd_turn():
    from fortress_director.settings import CREATIVITY_MOTIF_PROBABILITY

    original_prob = CREATIVITY_MOTIF_PROBABILITY
    # Force injection for test
    import fortress_director.settings

    fortress_director.settings.CREATIVITY_MOTIF_PROBABILITY = 1.0
    try:
        agent = CreativityAgent(client=DummyClient(), use_llm=False)
        event_output = {"scene": "Test scene", "options": [], "recent_motifs": []}
        # 3. turda motif injection beklenir
        with patch(
            "fortress_director.agents.creativity_agent.random.random", return_value=0.1
        ):
            enriched = agent.enrich_event(event_output, turn=3)
        assert enriched.get("motif_injected") in MOTIF_TABLE
        # 2. turda motif injection olmaz
        with patch(
            "fortress_director.agents.creativity_agent.random.random", return_value=0.1
        ):
            enriched2 = agent.enrich_event(event_output, turn=2)
        assert (
            "motif_injected" not in enriched2 or enriched2.get("motif_injected") is None
        )
    finally:
        fortress_director.settings.CREATIVITY_MOTIF_PROBABILITY = original_prob


def test_llm_rewrite_context():
    agent = CreativityAgent(client=DummyClient("Surprise!"), use_llm=True)
    event_output = {"scene": "Test scene", "options": []}
    enriched = agent.enrich_event(event_output, turn=1)
    assert enriched.get("scene") == "Surprise!"
    assert enriched.get("motif_injected") is None
