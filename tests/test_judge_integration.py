#!/usr/bin/env python3
"""Basit bir JudgeAgent ceza uygulama testi (yer değiştirilmiş)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fortress_director.agents.judge_agent import JudgeAgent


def test_judge_penalties_basic():
    judge = JudgeAgent()
    test_vars = {
        "WORLD_CONTEXT": "Test context",
        "content": (
            "A very happy, cheerful scene that contradicts the established gloomy atmosphere."
        ),
    }
    result = judge.evaluate(test_vars)
    assert isinstance(result, dict)
    # Çıktı sözlüğünde ceza alanları veya yumuşak düzenleme politikası beklenir
    assert any(
        key in result for key in ("penalty_magnitude", "penalty_applied", "soft_edit_policy")
    )

