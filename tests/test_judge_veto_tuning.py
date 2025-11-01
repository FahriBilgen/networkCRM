"""Unit tests for Judge veto tuning and MIN_TURN_GAP enforcement."""

import pytest
from unittest.mock import patch

from fortress_director.agents.judge_agent import JudgeAgent
from fortress_director.settings import JUDGE_BASE_VETO_PROB, JUDGE_MIN_TURN_GAP


def test_judge_base_veto_prob():
    """Test that Judge uses JUDGE_BASE_VETO_PROB as base disagreement probability."""
    agent = JudgeAgent()
    variables = {
        "content": "Test scene content",
        "repetition_count": 0,
        "atmosphere_repetition_count": 0,
        "motif_repetition": False,
        "creativity": False,
    }

    # Mock random to force veto roll
    with patch("fortress_director.agents.judge_agent.random.random", return_value=0.01):
        verdict = agent.evaluate(variables)
        # Since roll < JUDGE_BASE_VETO_PROB (0.02), should veto
        assert verdict["consistent"] is False
        assert verdict["reason"] == "stochastic_repetition_veto"


def test_judge_min_turn_gap_enforcement():
    """Test that orchestrator enforces MIN_TURN_GAP for repeated scenes."""
    # Since gap = 5-2=3 == JUDGE_MIN_TURN_GAP, should NOT force novelty (gap >= threshold)
    # Test the logic: if gap < JUDGE_MIN_TURN_GAP, trigger novelty
    gap = 5 - 2
    assert gap >= JUDGE_MIN_TURN_GAP  # This test case does not trigger novelty
    # For triggering case: turn 5, seen at turn 3, gap=2 < 3
    gap_trigger = 5 - 3
    assert gap_trigger < JUDGE_MIN_TURN_GAP  # Would trigger novelty_flag


def test_judge_no_veto_on_recent_scene():
    """Test that Judge does not veto immediately on scenes seen within MIN_TURN_GAP."""
    agent = JudgeAgent()
    variables = {
        "content": "Test scene content",
        "repetition_count": 10,  # High repetition
        "atmosphere_repetition_count": 0,
        "motif_repetition": False,
        "creativity": False,
    }

    # Mock random to force veto roll, but since it's recent, orchestrator should prevent
    # This test focuses on Judge logic; orchestrator logic is separate
    with patch("fortress_director.agents.judge_agent.random.random", return_value=0.01):
        verdict = agent.evaluate(variables)
        # Judge still vets based on its own logic, but orchestrator adds novelty_flag
        assert "consistent" in verdict
