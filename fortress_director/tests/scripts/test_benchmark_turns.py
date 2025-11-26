from pathlib import Path

from scripts import benchmark_turns


def test_benchmark_turns_no_llm(tmp_path, monkeypatch) -> None:
    fake_settings = type("S", (), {"log_dir": tmp_path})()
    monkeypatch.setattr(benchmark_turns, "SETTINGS", fake_settings)
    result = benchmark_turns.benchmark_turns(num_turns=2, use_llm=False)
    assert result["num_turns"] == 2
    assert result["use_llm"] is False
    assert "log_path" in result
    assert Path(result["log_path"]).exists()
