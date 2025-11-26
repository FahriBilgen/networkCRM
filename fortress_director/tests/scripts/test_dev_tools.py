from pathlib import Path

from scripts import dev_tools


def test_benchmark_turns_runs_without_llm(tmp_path: Path) -> None:
    result = dev_tools.benchmark_turns(num_turns=2, use_llm=False, log_dir=tmp_path)
    assert result.num_turns == 2
    assert len(result.durations) == 2
    assert result.total_seconds >= 0
    benchmark_files = list(tmp_path.glob("benchmark_*.json"))
    assert benchmark_files


def test_download_models_script_contains_commands() -> None:
    script_path = Path("scripts/download_models.sh")
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")
    assert "ollama pull" in content
