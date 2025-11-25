"""Centralised, deterministic settings used across Fortress Director."""

from __future__ import annotations

import errno
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

LOGGER = logging.getLogger(__name__)
_MISSING = object()


PROJECT_ROOT = Path(__file__).resolve().parent
# Repo kökünü fortress_director klasörünün bir üstü olarak kabul edelim
REPO_ROOT = PROJECT_ROOT.parent


ACTIVE_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class ModelConfig:
    """Read-only model configuration for a single agent."""

    name: str
    temperature: float
    top_p: float
    max_tokens: int
    top_k: int | None = None


@dataclass(frozen=True)
class LLMOptions:
    """Global default generation options shared by the simplified agents."""

    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int | None = 40


@dataclass(frozen=True)
class LLMRuntimeConfig:
    """Runtime knobs controlling caching/logging/timeout behavior."""

    # Timeout for LLM calls: 60s is reasonable for Ollama on local hw.
    # Prevents indefinite blocking if Ollama server is unresponsive.
    timeout_seconds: float = 60.0
    cache_ttl_seconds: int = 300
    max_retries: int = 1
    enable_cache: bool = True
    log_metrics: bool = True


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
    safe_function_gas_budget: int = 0
    default_locale: str = "en"
    safe_function_max_workers: int = 1
    llm_options: LLMOptions = field(default_factory=LLMOptions)
    llm_runtime: LLMRuntimeConfig = field(default_factory=LLMRuntimeConfig)
    # Timeouts used by lightweight LLM health checks (seconds)
    # Use large defaults to avoid spuriously marking models offline during
    # local development (effectively "no timeout").
    llm_status_list_timeout: float = 1e6
    llm_status_probe_timeout: float = 1e6


def _config_file() -> Path:
    return PROJECT_ROOT / "config" / "settings.yaml"


def _load_settings_overrides() -> Dict[str, Any]:
    """Load optional overrides from config/settings.yaml."""

    path = _config_file()
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        LOGGER.warning("Failed to parse %s: %s", path, exc)
        return {}
    if not isinstance(payload, dict):
        LOGGER.warning("settings.yaml must contain a mapping. Ignoring contents.")
        return {}
    return payload


def _resolve_path(value: Any) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    return candidate


def _resolve_float(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _resolve_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _resolve_optional_int(value: Any, fallback: int | None) -> int | None:
    if value is _MISSING:
        return fallback
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _merge_model_overrides(
    base: Mapping[str, ModelConfig], overrides: Mapping[str, Any]
) -> Dict[str, ModelConfig]:
    merged: Dict[str, ModelConfig] = dict(base)
    for key, payload in overrides.items():
        if isinstance(payload, str):
            payload_dict: Mapping[str, Any] = {"name": payload}
        elif isinstance(payload, Mapping):
            payload_dict = payload
        else:
            continue
        current = merged.get(key)
        if current is None:
            name = payload_dict.get("name")
            if not name:
                continue
            merged[key] = ModelConfig(
                name=str(name),
                temperature=_resolve_float(payload_dict.get("temperature", 0.7), 0.7),
                top_p=_resolve_float(payload_dict.get("top_p", 0.9), 0.9),
                max_tokens=_resolve_int(payload_dict.get("max_tokens", 256), 256),
                top_k=_resolve_optional_int(payload_dict.get("top_k", _MISSING), None),
            )
        else:
            merged[key] = ModelConfig(
                name=str(payload_dict.get("name", current.name)),
                temperature=_resolve_float(
                    payload_dict.get("temperature", current.temperature),
                    current.temperature,
                ),
                top_p=_resolve_float(
                    payload_dict.get("top_p", current.top_p), current.top_p
                ),
                max_tokens=_resolve_int(
                    payload_dict.get("max_tokens", current.max_tokens),
                    current.max_tokens,
                ),
                top_k=_resolve_optional_int(
                    payload_dict.get("top_k", _MISSING),
                    current.top_k,
                ),
            )
    return merged


def _coerce_llm_options(payload: Mapping[str, Any], current: LLMOptions) -> LLMOptions:
    temperature = _resolve_float(
        payload.get("temperature", current.temperature), current.temperature
    )
    top_p = _resolve_float(payload.get("top_p", current.top_p), current.top_p)
    top_k = _resolve_optional_int(payload.get("top_k", _MISSING), current.top_k)
    return LLMOptions(
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
    )


def _coerce_llm_runtime(
    payload: Mapping[str, Any],
    current: LLMRuntimeConfig,
) -> LLMRuntimeConfig:
    timeout_seconds = _resolve_float(
        payload.get("timeout_seconds", current.timeout_seconds),
        current.timeout_seconds,
    )
    cache_ttl = _resolve_int(
        payload.get("cache_ttl_seconds", current.cache_ttl_seconds),
        current.cache_ttl_seconds,
    )
    max_retries = _resolve_int(
        payload.get("max_retries", current.max_retries),
        current.max_retries,
    )
    enable_cache = bool(payload.get("enable_cache", current.enable_cache))
    log_metrics = bool(payload.get("log_metrics", current.log_metrics))
    return LLMRuntimeConfig(
        timeout_seconds=timeout_seconds,
        cache_ttl_seconds=cache_ttl,
        max_retries=max(0, max_retries),
        enable_cache=enable_cache,
        log_metrics=log_metrics,
    )


def _apply_llm_overrides(data: Dict[str, Any], payload: Any) -> None:
    if not isinstance(payload, Mapping):
        return
    ollama_block = payload.get("ollama")
    if isinstance(ollama_block, Mapping):
        base_url = ollama_block.get("base_url")
        if base_url:
            data["ollama_base_url"] = str(base_url)
        timeout = ollama_block.get("timeout")
        if timeout is not None:
            data["ollama_timeout"] = _resolve_float(timeout, data["ollama_timeout"])
    models_block = payload.get("models")
    if isinstance(models_block, Mapping):
        data["models"] = _merge_model_overrides(data["models"], models_block)
    options_block = payload.get("options")
    if isinstance(options_block, Mapping):
        data["llm_options"] = _coerce_llm_options(options_block, data["llm_options"])
    runtime_block = payload.get("runtime")
    if isinstance(runtime_block, Mapping):
        current_runtime = data.get("llm_runtime", LLMRuntimeConfig())
        data["llm_runtime"] = _coerce_llm_runtime(runtime_block, current_runtime)


def _apply_settings_overrides(settings: Settings) -> Settings:
    """Return a Settings instance with overrides applied."""

    overrides = _load_settings_overrides()
    if not overrides:
        return settings
    data = settings.__dict__.copy()
    data["models"] = dict(settings.models)
    data["llm_options"] = settings.llm_options
    data["llm_runtime"] = settings.llm_runtime
    path_fields = {"db_path", "world_state_path", "cache_dir", "log_dir"}
    float_fields = {"ollama_timeout"}
    int_fields = {
        "safe_function_gas_budget",
        "safe_function_max_workers",
        "max_active_models",
        "semantic_cache_ttl",
    }
    str_fields = {"ollama_base_url", "default_locale"}

    _apply_llm_overrides(data, overrides.get("llm"))

    for key, value in overrides.items():
        if key == "llm":
            continue
        if key == "models" and isinstance(value, Mapping):
            data["models"] = _merge_model_overrides(data["models"], value)
            continue
        if key not in data:
            continue
        if key in path_fields:
            if value is None:
                continue
            data[key] = _resolve_path(value)
        elif key in float_fields:
            data[key] = _resolve_float(value, data[key])
        elif key in int_fields:
            data[key] = _resolve_int(value, data[key])
        elif key in str_fields:
            data[key] = str(value)
    LOGGER.info("Applied overrides from %s", _config_file())
    return Settings(**data)


DEFAULT_WORLD_STATE = {
    "schema_version": ACTIVE_SCHEMA_VERSION,
    "campaign_id": "default_campaign",
    "turn_limit": 30,
    "current_turn": 0,
    "rng_seed": 12345,
    "scores": {
        "logic_score": 0,
        "emotion_score": 0,
        "corruption": 0,
    },
    "flags": [],
    "memory_layers": [],
    "active_layer": None,
    "npc_fragments": {},
    "inventory": [],
    "lore": {},
    "turn": 0,
    "day": 1,
    "time": "dawn",
    "locale": "en",
    "current_room": "entrance",
    "recent_events": [],
    "recent_motifs": [],
    "recent_world_atmospheres": [],
    "world_constraint_from_prev_turn": {
        "atmosphere": "low clouds hug the battlements",
        "sensory_details": ("Drums thud beyond the walls while the wind carries grit."),
    },
    "player": {
        "name": "The Shieldbearer",
        "inventory": ["oil lamp", "patched shield"],
        "stats": {"resolve": 3, "empathy": 2},
        "summary": "A weary defender holding the western wall.",
    },
    "character_summary": (
        "Rhea is loyal but impulsive; Boris is cautious and calculating."
    ),
    "relationship_summary": ("Rhea trusts the player; Boris weighs every trade."),
    "metrics": {
        "order": 50,
        "morale": 50,
        "resources": 40,
        "knowledge": 45,
        "corruption": 10,
        "glitch": 12,
        "risk_applied_total": 0,
        "major_flag_set": False,
        "major_events_triggered": 0,
        "major_event_last_turn": None,
        "combat": {
            "total_skirmishes": 0,
            "total_casualties_friendly": 0,
            "total_casualties_enemy": 0,
            "last_casualties_friendly": 0,
            "last_casualties_enemy": 0,
        },
    },
    "npc_trust": {},
    "environment_hazards": [],
    "weather_pattern": {
        "pattern": "overcast",
        "remaining": 0,
        "lock_until": 0,
    },
    "structures": {
        "western_wall": {
            "id": "western_wall",
            "kind": "wall",
            "x": 2,
            "y": 1,
            "durability": 80,
            "max_durability": 100,
            "status": "stable",
            "fortification": 0,
            "on_fire": False,
        },
        "inner_gate": {
            "id": "inner_gate",
            "kind": "gate",
            "x": 5,
            "y": 5,
            "durability": 70,
            "max_durability": 100,
            "status": "stable",
            "fortification": 0,
            "on_fire": False,
        },
        "watchtower": {
            "id": "watchtower",
            "kind": "tower",
            "x": 7,
            "y": 3,
            "durability": 60,
            "max_durability": 80,
            "status": "stable",
            "fortification": 0,
            "on_fire": False,
        },
        "granary": {
            "id": "granary",
            "kind": "storehouse",
            "x": 4,
            "y": 6,
            "durability": 55,
            "max_durability": 70,
            "status": "stable",
            "fortification": 0,
            "on_fire": False,
        },
    },
    "map_layers": {},
    "map_event_markers": [],
    "npc_roles": {},
    "npc_schedule": {},
    "patrols": {},
    "combat_log": [],
    "item_transfers": [],
    "stockpiles": {
        "food": 120,
        "wood": 60,
        "ore": 40,
    },
    "stockpile_log": [],
    "trade_routes": {},
    "trade_route_history": [],
    "scheduled_events": [],
    "story_progress": {
        "act": "build_up",
        "progress": 0.0,
        "act_history": [],
    },
    "timeline": [],
    "hazard_cooldowns": {},
    "schema_notes": {},
    "locked_options": {},
    # Drama governor memory
    "_drama_window": [],
    "_anomaly_active_until": None,
    "_world_lock_until": None,
    "_high_volatility_mode": False,
    "last_weather_change_turn": None,
}

SETTINGS = Settings(
    project_root=PROJECT_ROOT,
    db_path=PROJECT_ROOT / "db" / "game_state.sqlite",
    world_state_path=PROJECT_ROOT / "data" / "world_state.json",
    cache_dir=PROJECT_ROOT / "cache",
    # Tüm logları tek klasörde toplamak için depo kökünde logs kullan
    log_dir=REPO_ROOT / "logs",
    ollama_base_url="http://localhost:11434/",
    ollama_timeout=240.0,
    max_active_models=2,
    semantic_cache_ttl=86_400,
    models={
        "event": ModelConfig(
            name="phi3:mini",
            temperature=0.0,
            top_p=0.1,
            max_tokens=768,
        ),
        "world": ModelConfig(
            name="phi3:mini",
            temperature=0.1,
            top_p=0.4,
            max_tokens=384,
        ),
        "world_renderer": ModelConfig(
            name="phi3:mini",
            temperature=0.9,
            top_p=0.95,
            max_tokens=512,
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
        "director": ModelConfig(
            name="qwen2:1.5b",
            temperature=0.08,
            top_p=0.25,
            max_tokens=320,
        ),
        "planner": ModelConfig(
            name="qwen2:1.5b",
            temperature=0.05,
            top_p=0.2,
            max_tokens=256,
        ),
        "creativity": ModelConfig(
            name="gemma:2b",
            temperature=0.8,
            top_p=0.95,
            max_tokens=256,
        ),
    },
    llm_options=LLMOptions(
        temperature=0.7,
        top_p=0.9,
        top_k=40,
    ),
    llm_runtime=LLMRuntimeConfig(),
    safe_function_gas_budget=6,
    default_locale="en",
    safe_function_max_workers=4,
)
SETTINGS = _apply_settings_overrides(SETTINGS)

# Runtime tuning knobs for creativity and judge behaviour.
# These are intentionally module-level constants (simple to tweak during
# local testing). They are read by agent implementations.
# How often to consider injecting a motif (lower -> more frequent).
CREATIVITY_MOTIF_INTERVAL = 2
# When motif interval check passes, injection also happens stochastically
# according to this probability (0.0-1.0).
CREATIVITY_MOTIF_PROBABILITY = 0.35
# If True, creativity agent will be allowed to run in a lightweight
# "sandbox" mode that more aggressively rewrites scenes even if the
# surrounding filters are conservative.
CREATIVITY_FORCE_SANDBOX = False
# A suggested entropy/novelty threshold that higher-level orchestrator
# or event agent can consult (0.0-1.0). Lowering this makes creative
# triggers easier to pass.
CREATIVITY_TRIGGER_ENTROPY_THRESHOLD = 0.35

# Judge tuning: lower values make judge less biased toward always-approving
# (i.e., reduce conservative bias). Values should be (0.0-1.0).
JUDGE_BIAS_REWEIGHT = 0.3
# Judge thresholds
# If a Judge returns a tone_alignment score below this value the content
# will be considered misaligned and rejected by post-processing.
JUDGE_TONE_ALIGNMENT_THRESHOLD = 90
# Base stochastic veto probability (0.0-1.0); lowered to reduce aggressiveness.
JUDGE_BASE_VETO_PROB = 0.02
# Soft editing policy: cap how much normalization can happen per turn and
# require anomalies to persist for a short window so tension can breathe.
JUDGE_SOFT_MAX_CORRECTION_PER_TURN = (
    0.15  # allow more creative deviation before normalization
)
JUDGE_PERSIST_WINDOW = 4  # turns anomaly must be allowed to live
# Minimum turn gap before allowing veto on identical content.
JUDGE_MIN_TURN_GAP = 3
# Minimum interval between major events (turns).
MAJOR_EVENT_MIN_INTERVAL = 5
# Maximum motif injections per window (e.g., per 5 turns).
MAX_MOTIF_INJECTIONS_PER_WINDOW = 1
# Interval for motif injection attempts (every N turns) defined above as
# CREATIVITY_MOTIF_INTERVAL. Probability and sandbox flags are defined
# above as well; avoid duplicate definitions here.
# Pool of diverse event types to ensure variety and break repetition.
EVENT_DIVERSITY_POOL = [
    "siege_incident",
    "internal_conflict",
    "resource_scarcity",
    "diplomatic_encounter",
    "mystical_occurrence",
    "environmental_hazard",
    "personal_drama",
    "strategic_opportunity",
]

# World state persistence and drama tuning
# Minimum number of turns a world shift (e.g., weather/atmosphere) must
# persist.
WORLD_STATE_PERSIST_MIN_TURNS = 3

# Drama governor toggles low-variance runs into higher risk/novelty mode.
DRAMA_GOVERNOR_ENABLED = True
DRAMA_TARGET_VARIANCE = 10  # average absolute delta across core metrics
DRAMA_BOREDOM_WINDOW = 4  # turns to measure low variance before acting
RISK_BUDGET_DEFAULT = 3  # structural risk ops allowed per act

# High-volatility glitch mode scalar. Allows larger glitches when drama
# mode is active.
GLITCH_VOLATILITY_SCALAR = 3  # 1=default; 3=higher volatility in drama mode
GLITCH_MIN_FLOOR = 50  # baseline minimum glitch to avoid flat lines


def _safe_mkdir(path: Path) -> None:
    """Create a directory while tolerating read-only environments."""

    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        LOGGER.warning("Skipping creation of %s; permission denied", path)
    except OSError as exc:
        if exc.errno in (errno.EROFS, errno.EACCES):
            LOGGER.warning(
                "Skipping creation of %s; read-only filesystem (%s)",
                path,
                exc.strerror or exc.errno,
            )
        else:
            raise


def ensure_runtime_paths(settings: Settings = SETTINGS) -> None:
    """Create required directories deterministically if they are missing."""

    _safe_mkdir(settings.cache_dir)
    _safe_mkdir(settings.db_path.parent)
    _safe_mkdir(settings.world_state_path.parent)
    _safe_mkdir(settings.log_dir)


ensure_runtime_paths()
