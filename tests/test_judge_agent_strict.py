import pytest
from fortress_director.agents.judge_agent import JudgeAgent


import json


class DummyClient:
    def generate(self, **kwargs):
        # Simulate LLM output with low scores (as JSON string)
        return {
            "response": json.dumps(
                {
                    "consistent": True,
                    "coherence": 60,
                    "integrity": 80,
                    "tone_alignment": 80,
                    "reason": "Test: low coherence",
                }
            )
        }


def test_judge_agent_strict_threshold():
    agent = JudgeAgent(client=DummyClient())
    variables = {"content": "Test scene", "WORLD_CONTEXT": "dummy"}
    result = agent.evaluate(variables)
    assert result["consistent"] is False
    assert "coherence below threshold" in result["reason"]

    # Now test with low integrity
    class LowIntegrityClient:
        def generate(self, **kwargs):
            return {
                "response": json.dumps(
                    {
                        "consistent": True,
                        "coherence": 80,
                        "integrity": 70,
                        "tone_alignment": 80,
                        "reason": "Test: low integrity",
                    }
                )
            }

    agent2 = JudgeAgent(client=LowIntegrityClient())
    result2 = agent2.evaluate(variables)
    assert result2["consistent"] is False
    assert "integrity below threshold" in result2["reason"]

    # Now test with low tone_alignment
    class LowToneClient:
        def generate(self, **kwargs):
            return {
                "response": json.dumps(
                    {
                        "consistent": True,
                        "coherence": 80,
                        "integrity": 80,
                        "tone_alignment": 70,
                        "reason": "Test: low tone",
                    }
                )
            }

    agent3 = JudgeAgent(client=LowToneClient())
    result3 = agent3.evaluate(variables)
    assert result3["consistent"] is False
    assert "tone_alignment below threshold" in result3["reason"]

    # All high: should be consistent
    class AllHighClient:
        def generate(self, **kwargs):
            return {
                "response": json.dumps(
                    {
                        "consistent": True,
                        "coherence": 90,
                        "integrity": 90,
                        "tone_alignment": 90,
                        "reason": "All good",
                    }
                )
            }

    agent4 = JudgeAgent(client=AllHighClient())
    result4 = agent4.evaluate(variables)
    assert result4["consistent"] is True
