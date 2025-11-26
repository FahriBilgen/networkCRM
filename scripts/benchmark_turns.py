"""Benchmark helper that measures end-to-end turn latency."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fortress_director.core.state_store import GameState  # noqa: E402
from fortress_director.llm.metrics_logger import (  # noqa: E402
    register_metrics_callback,
)
from fortress_director.llm.runtime_mode import (  # noqa: E402
    is_llm_enabled,
    set_llm_enabled,
)
from fortress_director.pipeline.turn_manager import TurnManager  # noqa: E402
from fortress_director.settings import SETTINGS  # noqa: E402
from fortress_director.themes.loader import (  # noqa: E402
    BUILTIN_THEMES,
    load_theme_from_file,
)

DEFAULT_THEME_ID = "siege_default"
DEFAULT_CHOICES: Sequence[str] = ("option_1", "option_2", "option_3")


def benchmark_turns(num_turns: int = 10, use_llm: bool = True) -> Dict[str, Any]:
    """Run *num_turns* sequentially and capture timing/LLM stats."""

    if num_turns < 1:
        raise ValueError("num_turns must be >= 1")
    theme = load_theme_from_file(BUILTIN_THEMES[DEFAULT_THEME_ID])
    game_state = GameState.from_theme_config(theme)
    manager = TurnManager()
    durations: List[float] = []
    llm_calls = 0
    llm_failures = 0

    def _on_metric(metric) -> None:
        nonlocal llm_calls, llm_failures
        llm_calls += 1
        if not metric.success:
            llm_failures += 1

    unsubscribe = register_metrics_callback(_on_metric)
    previous_mode = is_llm_enabled()
    set_llm_enabled(use_llm)
    try:
        for turn_index in range(num_turns):
            choice_id = DEFAULT_CHOICES[turn_index % len(DEFAULT_CHOICES)]
            start = time.perf_counter()
            manager.run_turn(
                game_state,
                player_choice={"id": choice_id},
                theme=theme,
            )
            elapsed = time.perf_counter() - start
            durations.append(elapsed)
    finally:
        unsubscribe()
        set_llm_enabled(previous_mode)
    total_seconds = sum(durations)
    avg_seconds = total_seconds / num_turns if num_turns else 0.0
    min_seconds = min(durations) if durations else 0.0
    max_seconds = max(durations) if durations else 0.0
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "num_turns": num_turns,
        "use_llm": use_llm,
        "total_seconds": total_seconds,
        "average_seconds": avg_seconds,
        "min_seconds": min_seconds,
        "max_seconds": max_seconds,
        "durations": [round(value, 6) for value in durations],
        "llm_calls": llm_calls,
        "llm_failures": llm_failures,
        "created_at": timestamp,
    }
    logs_dir = SETTINGS.log_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_path = logs_dir / f"benchmark_{timestamp}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["log_path"] = str(output_path)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark Fortress Director turns.")
    parser.add_argument(
        "--num-turns",
        type=int,
        default=10,
        help="Number of turns to execute (default: 10)",
    )
    llm_group = parser.add_mutually_exclusive_group()
    llm_group.add_argument(
        "--use-llm",
        dest="use_llm",
        action="store_true",
        help="Enable live LLM calls during the benchmark (default).",
    )
    llm_group.add_argument(
        "--no-llm",
        dest="use_llm",
        action="store_false",
        help="Disable live LLM calls (use deterministic fallbacks).",
    )
    parser.set_defaults(use_llm=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    result = benchmark_turns(num_turns=args.num_turns, use_llm=args.use_llm)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
