from __future__ import annotations

import hashlib
import importlib
import json
import logging
import shutil
from pathlib import Path
from typing import Dict

import pytest

from fortress_director.agents.judge_agent import check_win_loss
from fortress_director.settings import Settings, ensure_runtime_paths
from fortress_director.utils.metrics_manager import MetricManager
from fortress_director.utils.glitch_manager import GlitchManager


def test_metric_manager_clamps_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    state: Dict[str, object] = {"metrics": {"order": 95}}
    manager = MetricManager(state, log_sink=[])

    with caplog.at_level(logging.DEBUG):
        result = manager.adjust_metric("order", 10, cause="test:order_clamp")

    assert result == 100
    assert manager.log_sink is not None
    assert manager.log_sink[-1]["value"] == 100
    messages = {record.getMessage() for record in caplog.records}
    assert any("Metric 'order' updated" in message for message in messages)
    assert any("Clamped metric value" in message for message in messages)


def test_glitch_manager_deterministic_roll(caplog: pytest.LogCaptureFixture) -> None:
    state: Dict[str, object] = {"metrics": {}}
    metrics = MetricManager(state, log_sink=[])
    glitch_manager = GlitchManager(seed=1234)

    with caplog.at_level(logging.INFO):
        result = glitch_manager.resolve_turn(metrics=metrics, turn=2)

    expected_roll = int.from_bytes(
        hashlib.sha256(f"{1234}:{2}:{12}".encode("utf-8")).digest()[:4], "big"
    ) % 101
    assert result["roll"] == expected_roll
    assert any(
        "Glitch roll complete" in record.getMessage() for record in caplog.records
    )


def test_check_win_loss_reasons(caplog: pytest.LogCaptureFixture) -> None:
    scenarios = [
        (
            {"order": 80, "morale": 75, "glitch": 20, "resources": 40},
            {"status": "win", "reason": "fortress_stabilized"},
        ),
        (
            {"order": 10, "morale": 50, "glitch": 10, "resources": 20},
            {"status": "loss", "reason": "order_collapse"},
        ),
        (
            {"order": 40, "morale": 40, "glitch": 90, "resources": 30},
            {"status": "loss", "reason": "glitch_overload"},
        ),
    ]

    for metrics, expected in scenarios:
        caplog.clear()
        with caplog.at_level(logging.INFO):
            outcome = check_win_loss(metrics, turn=1, turn_limit=10)
        assert outcome == expected
        assert any(
            "Win/loss evaluation result" in record.getMessage()
            for record in caplog.records
        )


def test_orchestrator_end_to_end_logging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings_mod = importlib.import_module("fortress_director.settings")
    orchestrator_mod = importlib.import_module(
        "fortress_director.orchestrator.orchestrator"
    )
    base_agent_mod = importlib.import_module("fortress_director.agents.base_agent")

    base_settings = settings_mod.SETTINGS
    sandbox = Settings(
        project_root=tmp_path,
        db_path=tmp_path / "db" / "game_state.sqlite",
        world_state_path=tmp_path / "data" / "world_state.json",
        cache_dir=tmp_path / "cache",
        log_dir=tmp_path / "logs",
        ollama_base_url=base_settings.ollama_base_url,
        ollama_timeout=base_settings.ollama_timeout,
        max_active_models=base_settings.max_active_models,
        semantic_cache_ttl=base_settings.semantic_cache_ttl,
        models=dict(base_settings.models),
    )
    ensure_runtime_paths(sandbox)
    shutil.copytree(
        settings_mod.PROJECT_ROOT / "prompts",
        sandbox.project_root / "prompts",
    )
    (sandbox.world_state_path).write_text(
        json.dumps(settings_mod.DEFAULT_WORLD_STATE, indent=2),
        encoding="utf-8",
    )

    monkeypatch.setattr(settings_mod, "SETTINGS", sandbox, raising=False)
    monkeypatch.setattr(orchestrator_mod, "SETTINGS", sandbox, raising=False)
    monkeypatch.setattr(base_agent_mod, "SETTINGS", sandbox, raising=False)

    orchestrator = orchestrator_mod.Orchestrator.build_default()

    with caplog.at_level(logging.INFO):
        result = orchestrator.run_turn()

    assert "glitch" in result
    assert "win_loss" in result
    assert any(
        "Turn execution started." in record.getMessage() for record in caplog.records
    )
    assert any(
        "Glitch resolution outcome" in record.getMessage()
        for record in caplog.records
    )
    assert any(
        "Win/loss status after turn" in record.getMessage()
        for record in caplog.records
    )
