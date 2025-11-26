import json

from fortress_director.llm.metrics_logger import LOG_PATH, log_llm_metrics
from fortress_director.llm.profiler import LLMCallMetrics


def test_log_llm_metrics_appends_json_lines(tmp_path) -> None:
    log_file = tmp_path / "llm_calls.log"
    original_path = LOG_PATH
    try:
        # Redirect logger output to the temp path.
        import fortress_director.llm.metrics_logger as metrics_logger

        metrics_logger.LOG_PATH = log_file
        captured: list[object] = []
        unsubscribe = metrics_logger.register_metrics_callback(
            lambda metric: captured.append(metric)
        )
        sample = LLMCallMetrics(
            agent="director",
            model_name="mistral",
            duration_ms=123.4,
            prompt_tokens=100,
            completion_tokens=64,
            success=True,
        )
        log_llm_metrics(sample)
        failure = LLMCallMetrics(
            agent="planner",
            model_name="mock",
            duration_ms=10.0,
            prompt_tokens=None,
            completion_tokens=None,
            success=False,
            error_type="TimeoutError",
        )
        log_llm_metrics(failure)
    finally:
        import fortress_director.llm.metrics_logger as metrics_logger

        if "unsubscribe" in locals():
            unsubscribe()
        metrics_logger.LOG_PATH = original_path
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["agent"] == "director"
    assert first["success"] is True
    second = json.loads(lines[1])
    assert second["error_type"] == "TimeoutError"
    assert len(captured) == 2
    assert captured[1].error_type == "TimeoutError"
