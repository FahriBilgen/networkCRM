from __future__ import annotations

from pathlib import Path

from fortress_director import settings as settings_module


def test_llm_runtime_overrides_from_config(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "\n".join(
            [
                "llm:",
                "  runtime:",
                "    timeout_seconds: 5",
                "    cache_ttl_seconds: 42",
                "    max_retries: 3",
                "    enable_cache: false",
                "    log_metrics: false",
            ]
        ),
        encoding="utf-8",
    )

    def _fake_config_file() -> Path:
        return config_path

    monkeypatch.setattr(settings_module, "_config_file", _fake_config_file)
    reloaded = settings_module._apply_settings_overrides(settings_module.SETTINGS)
    runtime = reloaded.llm_runtime
    assert runtime.timeout_seconds == 5
    assert runtime.cache_ttl_seconds == 42
    assert runtime.max_retries == 3
    assert runtime.enable_cache is False
    assert runtime.log_metrics is False
