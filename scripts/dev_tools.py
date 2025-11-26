"""Developer utilities for deterministic smoke testing."""
# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
import logging
import random
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fortress_director.core.state_store import GameState
from fortress_director.llm.model_registry import get_registry
from fortress_director.llm.ollama_client import OllamaClient, OllamaClientError
from fortress_director.llm.runtime_mode import is_llm_enabled, set_llm_enabled
from fortress_director.pipeline.turn_manager import run_turn
from fortress_director.settings import SETTINGS

import scripts.llm_perf_report as perf_report

LOGGER = logging.getLogger(__name__)
DEFAULT_SCRIPTED_CHOICES: Sequence[str] = (
    "option_1",
    "option_2",
    "option_1",
    "option_3",
)
DEFAULT_LOG_DIR = ROOT_DIR / "logs"


def run_smoke_test(
    num_runs: int = 20,
    *,
    seed: int | None = None,
    scripted_choices: Sequence[str] | None = None,
) -> bool:
    """Execute repeated pipeline runs and report whether the loop stayed crash-free."""

    if num_runs < 1:
        raise ValueError("num_runs must be >= 1")
    rng_seed = seed if seed is not None else 1337
    rng = random.Random(rng_seed)
    choices = list(scripted_choices or DEFAULT_SCRIPTED_CHOICES)
    if not choices:
        choices = ["option_1"]

    game_state = GameState()
    min_stability = float("inf")
    for iteration in range(num_runs):
        if iteration < len(choices):
            choice = choices[iteration]
        else:
            choice = rng.choice(choices)
        try:
            payload = run_turn(game_state, player_choice={"id": choice})
        except Exception:  # pragma: no cover - dev-time guard
            LOGGER.exception(
                "Smoke test failed on iteration %s (choice=%s)", iteration + 1, choice
            )
            return False
        executed = payload.executed_actions or []
        if not executed:
            LOGGER.error(
                "Smoke test aborted: no safe functions executed on iteration %s.",
                iteration + 1,
            )
            return False
        projected = game_state.get_projected_state()
        stability = int(projected.get("world", {}).get("stability", 0))
        min_stability = min(min_stability, stability)
        if (iteration + 1) % 5 == 0 or (iteration + 1) == num_runs:
            LOGGER.info(
                "Smoke %s/%s | choice=%s | executed=%s | stability=%s",
                iteration + 1,
                num_runs,
                choice,
                len(executed),
                stability,
            )
    LOGGER.info(
        "Smoke test PASS: %s runs without crashes (min stability %s).",
        num_runs,
        int(min_stability),
    )
    return True


def benchmark_turns(
    num_turns: int = 10,
    *,
    use_llm: bool = True,
    log_dir: Path | None = None,
    scripted_choices: Sequence[str] | None = None,
) -> BenchmarkResult:
    """Benchmark repeated turns and persist timing metadata."""

    if num_turns < 1:
        raise ValueError("num_turns must be >= 1")
    choices = list(scripted_choices or DEFAULT_SCRIPTED_CHOICES)
    if not choices:
        choices = ["option_1"]
    log_dir = log_dir or DEFAULT_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    previous_llm_state = is_llm_enabled()
    set_llm_enabled(use_llm)
    try:
        game_state = GameState()
        durations: list[float] = []
        for turn_index in range(num_turns):
            player_choice = {"id": choices[turn_index % len(choices)]}
            start = time.perf_counter()
            run_turn(game_state, player_choice=player_choice)
            elapsed = time.perf_counter() - start
            durations.append(elapsed)
            LOGGER.info(
                "Benchmark turn %s/%s choice=%s duration=%.3fs",
                turn_index + 1,
                num_turns,
                player_choice["id"],
                elapsed,
            )
        total = sum(durations)
        avg = statistics.fmean(durations)
        result = BenchmarkResult(
            num_turns=num_turns,
            durations=durations,
            total_seconds=total,
            average_seconds=avg,
            min_seconds=min(durations),
            max_seconds=max(durations),
            created_at=datetime.now(timezone.utc).isoformat(),
            use_llm=use_llm,
        )
        _persist_benchmark_result(result, log_dir)
        LOGGER.info(
            "Benchmark complete: total=%.2fs avg=%.3fs min=%.3fs max=%.3fs",
            result.total_seconds,
            result.average_seconds,
            result.min_seconds,
            result.max_seconds,
        )
        return result
    finally:
        set_llm_enabled(previous_llm_state)


def summarize_llm_calls(limit: int | None = None) -> dict[str, object]:
    """Return aggregated stats for the LLM profiler log."""

    log_path = SETTINGS.log_dir / "llm_calls.log"
    if limit is None or limit <= 0 or not log_path.exists():
        return perf_report.summarize_llm_metrics(log_path)
    with log_path.open("r", encoding="utf-8") as handle:
        lines = handle.readlines()
    subset = (line.strip() for line in lines[-limit:])
    return perf_report.summarize_llm_metrics_from_lines(
        line for line in subset if line
    )


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _handle_smoke_test(args: argparse.Namespace) -> int:
    ok = run_smoke_test(num_runs=args.runs, seed=args.seed)
    return 0 if ok else 1


def _persist_benchmark_result(result: BenchmarkResult, log_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = log_dir / f"benchmark_{timestamp}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, indent=2)
    return path


def _handle_benchmark(args: argparse.Namespace) -> int:
    benchmark_turns(num_turns=args.runs, use_llm=args.use_llm)
    return 0


def _handle_llm_summary(args: argparse.Namespace) -> int:
    summary = summarize_llm_calls(limit=args.limit)
    print(json.dumps(summary, indent=2))
    return 0


def check_llm_health() -> bool:
    """Verify that each registered model can answer a ping prompt."""

    registry = get_registry()
    client = OllamaClient()
    ok = True
    for record in registry.list():
        try:
            client.generate(
                model=record.config.name,
                prompt="ping",
                options={"num_predict": 1},
            )
            print(f"[OK] {record.agent}: {record.config.name}")
        except OllamaClientError as exc:
            ok = False
            print(f"[FAIL] {record.agent}: {record.config.name} - {exc}")
    return ok


def _handle_check_llm(_: argparse.Namespace) -> int:
    ok = check_llm_health()
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Developer helpers for Fortress Director"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging verbosity (default: INFO)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    smoke_parser = subparsers.add_parser(
        "smoke_test",
        help="Run repeated turns to ensure demo stability",
    )
    smoke_parser.add_argument(
        "--runs",
        type=int,
        default=20,
        help="Number of sequential runs to execute (default: 20)",
    )
    smoke_parser.add_argument(
        "--seed",
        type=int,
        help="Optional RNG seed for reproducible choice selection",
    )
    smoke_parser.set_defaults(handler=_handle_smoke_test)
    health_parser = subparsers.add_parser(
        "check_llm",
        help="Ping each configured Ollama model to confirm availability",
    )
    health_parser.set_defaults(handler=_handle_check_llm)
    benchmark_parser = subparsers.add_parser(
        "benchmark",
        help="Run repeated turns and capture timing metrics",
    )
    benchmark_parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Number of turns to execute (default: 10)",
    )
    llm_group = benchmark_parser.add_mutually_exclusive_group()
    llm_group.add_argument(
        "--use-llm",
        dest="use_llm",
        action="store_true",
        help="Enable live LLM calls during the benchmark",
    )
    llm_group.add_argument(
        "--no-llm",
        dest="use_llm",
        action="store_false",
        help="Disable LLM calls (deterministic fallbacks)",
    )
    benchmark_parser.set_defaults(use_llm=True)
    benchmark_parser.set_defaults(handler=_handle_benchmark)
    llm_summary_parser = subparsers.add_parser(
        "llm_summary",
        help="Summarize profiler output for recent LLM calls",
    )
    llm_summary_parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of recent entries considered",
    )
    llm_summary_parser.set_defaults(handler=_handle_llm_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)
    handler = getattr(args, "handler")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())


@dataclass
class BenchmarkResult:
    num_turns: int
    durations: list[float]
    total_seconds: float
    average_seconds: float
    min_seconds: float
    max_seconds: float
    created_at: str
    use_llm: bool

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["durations"] = [round(value, 6) for value in self.durations]
        return payload
