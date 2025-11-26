"""Simple CLI that summarizes LLM metrics logs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fortress_director.settings import SETTINGS  # noqa: E402


def summarize_llm_metrics(log_path: str | Path = SETTINGS.log_dir / "llm_calls.log") -> Dict[str, Any]:
    """Parse *log_path* and aggregate LLM call performance metrics."""

    path = Path(log_path)
    if not path.exists():
        return _empty_summary()
    return summarize_llm_metrics_from_lines(_iter_log_lines(path))


def summarize_llm_metrics_from_lines(lines: Iterable[str]) -> Dict[str, Any]:
    total_calls = 0
    failures = 0
    durations: list[float] = []
    per_agent: Dict[str, Dict[str, Any]] = {}
    for line in lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        agent = str(payload.get("agent") or "unknown")
        duration = float(payload.get("duration_ms") or 0.0)
        success = bool(payload.get("success", True))
        total_calls += 1
        if not success:
            failures += 1
        durations.append(duration)
        stats = per_agent.setdefault(
            agent,
            {"durations": [], "failures": 0, "calls": 0},
        )
        stats["durations"].append(duration)
        stats["calls"] += 1
        if not success:
            stats["failures"] += 1
    avg_duration = sum(durations) / total_calls if total_calls else 0.0
    max_duration = max(durations) if durations else 0.0
    if total_calls == 0:
        return _empty_summary()
    return {
        "total_calls": total_calls,
        "avg_duration_ms": avg_duration,
        "max_duration_ms": max_duration,
        "failure_rate": (failures / total_calls) if total_calls else 0.0,
        "per_agent": {
            agent: {
                "calls": stats["calls"],
                "avg_duration_ms": (
                    sum(stats["durations"]) / stats["calls"] if stats["calls"] else 0.0
                ),
                "max_duration_ms": max(stats["durations"]) if stats["durations"] else 0.0,
                "failure_rate": (
                    stats["failures"] / stats["calls"] if stats["calls"] else 0.0
                ),
            }
            for agent, stats in per_agent.items()
        },
    }


def _iter_log_lines(path: Path) -> Iterable[str]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield line


def _empty_summary() -> Dict[str, Any]:
    return {
        "total_calls": 0,
        "avg_duration_ms": 0.0,
        "max_duration_ms": 0.0,
        "failure_rate": 0.0,
        "per_agent": {},
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize LLM metrics log.")
    parser.add_argument(
        "--log-path",
        default=str(SETTINGS.log_dir / "llm_calls.log"),
        help="Path to llm_calls.log file (default: %(default)s)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    summary = summarize_llm_metrics(args.log_path)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
