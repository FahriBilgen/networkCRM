#!/usr/bin/env python3
"""Simple test script to validate judge agent penalty application."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fortress_director.agents.judge_agent import JudgeAgent


def test_judge_penalties():
    """Test that judge agent applies penalties correctly."""
    judge = JudgeAgent()

    # Test case with low tone alignment
    test_vars = {
        "WORLD_CONTEXT": "Test context",
        "content": "A very happy, cheerful scene that contradicts "
        "the established gloomy atmosphere.",
    }

    result = judge.evaluate(test_vars)
    print(f"Judge result: {result}")

    # Check for penalty fields
    assert "penalty_applied" in result
    assert "penalty_magnitude" in result

    if result.get("tone_alignment", 100) < 75:
        assert result["penalty_applied"] in ["minor_penalty", "major_penalty"]
        assert isinstance(result["penalty_magnitude"], dict)

    print("✓ Judge agent penalty system working correctly")


if __name__ == "__main__":
    test_judge_penalties()
