"""Centralised, deterministic settings used across Fortress Director."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ModelConfig:
    """Read-only model configuration for a single agent."""

    name: str
    temperature: float
    top_p: float
    max_tokens: int


@dataclass(frozen=True)
class Settings:
    """Immutable settings bundle for the entire engine."""

    project_root: Path
    db_path: Path
    world_state_path: Path
    cache_dir: Path
    log_dir: Path
    ollama_base_url: str
    ollama_timeout: float
    max_active_models: int
    semantic_cache_ttl: int
    models: Mapping[str, ModelConfig]


SETTINGS = Settings(
    project_root=PROJECT_ROOT,
    db_path=PROJECT_ROOT / "db" / "game_state.sqlite",
    world_state_path=PROJECT_ROOT / "data" / "world_state.json",
    cache_dir=PROJECT_ROOT / "cache",
    log_dir=PROJECT_ROOT / "logs",
    ollama_base_url="http://localhost:11434/",
    ollama_timeout=240.0,
    max_active_models=2,
    semantic_cache_ttl=86_400,
    models={
        "event": ModelConfig(
            name="mistral",
            temperature=0.2,
            top_p=0.5,
            max_tokens=512,
        ),
        "world": ModelConfig(
            name="phi3:mini",
            temperature=0.1,
            top_p=0.4,
            max_tokens=384,
        ),
        "character": ModelConfig(
            name="gemma:2b",
            temperature=0.35,
            top_p=0.7,
            max_tokens=768,
        ),
        "judge": ModelConfig(
            name="qwen2:1.5b",
            temperature=0.05,
            top_p=0.2,
            max_tokens=256,
        ),
    },
)


def ensure_runtime_paths(settings: Settings = SETTINGS) -> None:
    """Create required directories deterministically if they are missing."""

    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.world_state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)


ensure_runtime_paths()
