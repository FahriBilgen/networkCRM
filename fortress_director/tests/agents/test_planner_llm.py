import json
import logging
from unittest.mock import MagicMock

import pytest

from fortress_director.agents import PlannerAgent
from fortress_director.core.state_store import GameState
from fortress_director.llm.ollama_client import OllamaClientError
from fortress_director.llm.runtime_mode import set_llm_enabled


@pytest.fixture(autouse=True)
def enable_llm_for_tests():
    """Ensure LLM mode is enabled for all tests in this module."""
    set_llm_enabled(True)
    yield
    set_llm_enabled(True)


def _sample_scene_intent() -> dict:
    return {"focus": "explore", "summary": "Scout the ruins."}


def _projected_state() -> dict:
    return GameState().get_projected_state()


def test_planner_agent_parses_llm_plan() -> None:
    mock_client = MagicMock()
    response_payload = {
        "gas": 1,
        "calls": [
            {"name": "adjust_metric", "kwargs": {"metric": "order", "delta": 1}},
            {"name": "set_flag", "kwargs": {"flag": "reserved_option"}},
        ],
    }
    mock_client.generate.return_value = {"response": json.dumps(response_payload)}
    projected_state = _projected_state()
    planner = PlannerAgent(llm_client=mock_client)
    payload = planner.plan_actions(projected_state, _sample_scene_intent())
    assert payload["planned_actions"][0]["function"] == "adjust_metric"
    assert payload["planned_actions"][0]["args"]["metric"] == "order"
    mock_client.generate.assert_called_once()


def test_planner_agent_falls_back_when_llm_errors() -> None:
    mock_client = MagicMock()
    mock_client.generate.side_effect = OllamaClientError("timeout")
    projected_state = _projected_state()
    planner = PlannerAgent(llm_client=mock_client)
    payload = planner.plan_actions(projected_state, _sample_scene_intent())
    assert payload["planned_actions"]
    functions = [action["function"] for action in payload["planned_actions"]]
    assert "set_flag" in functions


def test_build_prompt_mentions_guardrails() -> None:
    planner = PlannerAgent(llm_client=MagicMock())
    projected_state = _projected_state()
    prompt = planner.build_prompt(projected_state, _sample_scene_intent())
    assert "max 3 calls" in prompt.lower()
    assert "no $schema" in prompt.lower()


def test_validate_llm_output_rejects_schema_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    planner = PlannerAgent(llm_client=MagicMock())
    caplog.set_level(logging.ERROR)
    payload = {
        "gas": 1,
        "$schema": "https://example.com/schema",
        "calls": [
            {"name": "adjust_metric", "kwargs": {"metric": "order", "delta": 1}},
        ],
    }
    with pytest.raises(ValueError):
        planner.validate_llm_output(payload)
    assert any(
        "planner_invalid_schema_output" in record.message for record in caplog.records
    )


def test_validate_llm_output_infers_gas_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    planner = PlannerAgent(llm_client=MagicMock())
    caplog.set_level(logging.INFO)
    payload = json.dumps(
        {
            "calls": [
                {"name": "adjust_metric", "kwargs": {"metric": "order", "delta": 1}},
                {"name": "set_flag", "kwargs": {"flag": "reserve_option"}},
            ],
        },
    )
    result = planner.validate_llm_output(payload)
    assert result["gas"] == 2
    assert any("planner_gas_inferred" in record.message for record in caplog.records)
