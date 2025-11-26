import json

from scripts import llm_perf_report


def test_summarize_llm_metrics_parses_log(tmp_path) -> None:
    log_file = tmp_path / "llm_calls.log"
    entries = [
        {
            "agent": "director",
            "model": "mistral",
            "duration_ms": 120.0,
            "success": True,
            "error_type": None,
        },
        {
            "agent": "planner",
            "model": "qwen",
            "duration_ms": 80.0,
            "success": False,
            "error_type": "TimeoutError",
        },
    ]
    log_file.write_text(
        "\n".join(json.dumps(entry) for entry in entries) + "\n",
        encoding="utf-8",
    )
    summary = llm_perf_report.summarize_llm_metrics(log_file)
    assert summary["total_calls"] == 2
    assert summary["failure_rate"] == 0.5
    assert summary["per_agent"]["planner"]["failure_rate"] == 1.0
    assert summary["per_agent"]["director"]["calls"] == 1
