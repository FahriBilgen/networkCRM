"""Centralised, deterministic settings used across Fortress Director."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parent
# Repo kökünü (proje kökü) fortress_director klasörünün bir üstü olarak kabul edelim
REPO_ROOT = PROJECT_ROOT.parent


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
    safe_function_gas_budget: int = 0


DEFAULT_WORLD_STATE = {
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
    "current_room": "entrance",
    "recent_events": [],
    "recent_motifs": [],
    "world_constraint_from_prev_turn": {
        "atmosphere": "low clouds hug the battlements",
        "sensory_details": "Drums thud beyond the walls while the wind carries grit.",
    },
    "player": {
        "name": "The Shieldbearer",
        "inventory": ["oil lamp", "patched shield"],
        "stats": {"resolve": 3, "empathy": 2},
        "summary": "A weary defender holding the western wall.",
    },
    "character_summary": "Rhea is loyal but impulsive; Boris is cautious and calculating.",
    "relationship_summary": "Rhea trusts the player; Boris weighs every trade.",
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
    },
    "npc_trust": {},
    # Drama governor memory
    "_drama_window": [],
    "_anomaly_active_until": None,
    "_world_lock_until": None,
    "_high_volatility_mode": False,
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
    safe_function_gas_budget=6,
)

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
JUDGE_SOFT_MAX_CORRECTION_PER_TURN = 0.15  # allow more creative deviation before normalization
JUDGE_PERSIST_WINDOW = 4  # turns anomaly must be allowed to live
# Minimum turn gap before allowing veto on identical content.
JUDGE_MIN_TURN_GAP = 3
# Minimum interval between major events (turns).
MAJOR_EVENT_MIN_INTERVAL = 5
# Maximum motif injections per window (e.g., per 5 turns).
MAX_MOTIF_INJECTIONS_PER_WINDOW = 1
# Interval for motif injection attempts (every N turns) defined above as CREATIVITY_MOTIF_INTERVAL.
# Probability and sandbox flags are also defined above; avoid duplicate definitions.
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
# Minimum number of turns a world shift (e.g., weather/atmosphere) must persist.
WORLD_STATE_PERSIST_MIN_TURNS = 3

# Drama governor toggles low-variance runs into higher risk/novelty mode.
DRAMA_GOVERNOR_ENABLED = True
DRAMA_TARGET_VARIANCE = 10          # average absolute delta across core metrics
DRAMA_BOREDOM_WINDOW = 4            # turns to measure low variance before acting
RISK_BUDGET_DEFAULT = 3             # structural risk ops allowed per act

# High-volatility glitch mode scalar. Allows larger glitches when drama mode on.
GLITCH_VOLATILITY_SCALAR = 3        # 1=default; 3=higher volatility in drama mode
GLITCH_MIN_FLOOR = 50              # baseline minimum glitch to avoid flat lines


def ensure_runtime_paths(settings: Settings = SETTINGS) -> None:
    """Create required directories deterministically if they are missing."""

    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.world_state_path.parent.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)


ensure_runtime_paths()
