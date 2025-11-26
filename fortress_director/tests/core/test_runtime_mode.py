import importlib
import sys
from types import ModuleType
from typing import Dict

import pytest

MODULE_NAME = "fortress_director.llm.runtime_mode"


def _reload_with_env(
    monkeypatch: pytest.MonkeyPatch, env: Dict[str, str]
) -> ModuleType:
    for key in ("FORTRESS_LLM_MODE", "FORTRESS_OFFLINE"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]
    return importlib.import_module(MODULE_NAME)


@pytest.fixture(autouse=True)
def _reset_runtime_mode(monkeypatch: pytest.MonkeyPatch):
    yield
    for key in ("FORTRESS_LLM_MODE", "FORTRESS_OFFLINE"):
        monkeypatch.delenv(key, raising=False)
    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]
    importlib.import_module(MODULE_NAME)


def test_loads_stub_mode_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mode = _reload_with_env(monkeypatch, {"FORTRESS_LLM_MODE": "stub"})
    assert runtime_mode.get_mode() == "stub"
    assert not runtime_mode.is_llm_enabled()


def test_offline_flag_forces_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mode = _reload_with_env(monkeypatch, {"FORTRESS_OFFLINE": "1"})
    assert runtime_mode.get_mode() == "stub"


def test_set_llm_enabled_updates_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    runtime_mode = _reload_with_env(monkeypatch, {"FORTRESS_LLM_MODE": "stub"})
    runtime_mode.set_llm_enabled(True)
    assert runtime_mode.get_mode() == "llm"
