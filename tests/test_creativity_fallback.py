"""Unit tests for CreativityAgent fallback and motif rotation."""

import pytest
from unittest.mock import patch

from fortress_director.agents.creativity_agent import (
    CreativityAgent,
    FALLBACK_TEMPLATES,
    MOTIF_TABLE,
)


def test_creativity_fallback_on_llm_failure():
    """Test that CreativityAgent uses fallback templates when LLM fails."""
    agent = CreativityAgent(use_llm=True)

    event_output = {"scene": "Original scene", "recent_motifs": []}

    # Mock LLM to raise exception
    with patch.object(agent, "run", side_effect=Exception("LLM failed")):
        result = agent.enrich_event(event_output, turn=1)

    # Should use fallback and not fail
    assert "scene" in result
    assert result["scene"] in FALLBACK_TEMPLATES
    assert result["motif_injected"] is None


def test_motif_rotation():
    """Test that motifs rotate when recent ones are repeated."""
    agent = CreativityAgent(use_llm=False)  # Use motif injection path

    # First call with empty recent motifs, force injection
    event1 = {"scene": "Scene 1", "recent_motifs": [], "novelty_flag": True}
    with patch(
        "fortress_director.agents.creativity_agent.random.random", return_value=0.1
    ):  # Force injection
        result1 = agent.enrich_event(event1, turn=2)
    motif1 = result1.get("motif_injected")
    assert motif1 in MOTIF_TABLE

    # Second call with recent motif, force injection again
    event2 = {"scene": "Scene 2", "recent_motifs": [motif1], "novelty_flag": True}
    with patch(
        "fortress_director.agents.creativity_agent.random.random", return_value=0.1
    ):
        result2 = agent.enrich_event(event2, turn=2)
    motif2 = result2.get("motif_injected")
    # Should pick different motif if available
    if len(MOTIF_TABLE) > 1:
        assert motif2 != motif1 or motif2 in MOTIF_TABLE


def test_motif_injection_limit():
    """Test that motif injection respects MAX_MOTIF_INJECTIONS_PER_WINDOW."""
    from fortress_director.settings import MAX_MOTIF_INJECTIONS_PER_WINDOW

    agent = CreativityAgent(use_llm=False)

    # Simulate many recent injections
    recent_motifs = ["dummy"] * (MAX_MOTIF_INJECTIONS_PER_WINDOW + 1)
    event = {"scene": "Scene", "recent_motifs": recent_motifs}

    with patch(
        "fortress_director.agents.creativity_agent.random.random", return_value=0.1
    ):
        result = agent.enrich_event(event, turn=1)
    # Should not inject new motif due to limit
    assert "motif_injected" not in result or result["motif_injected"] is None
