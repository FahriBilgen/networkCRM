#!/usr/bin/env python3
"""Run a profiling session and emit a weekly-style KPI report."""

from __future__ import annotations

import argparse
import json
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Tuple

import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from tools.profile_turn import ProfileRun
from tools.telemetry_report import load_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a profiling session and store KPI snapshots.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=3,
        help="Number of sequential turns to profile (default: 3).",
    )
    parser.add_argument(
        "--tag",
        help="Optional suffix for the profiling run directory.",
    )
    parser.add_argument(
        "--random-choice",
        action="store_true",
        help="Request a random option each turn.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset world state before profiling.",
    )
    parser.add_argument(
        "--keep-state",
        action="store_true",
        help="Persist state mutations after profiling completes.",
    )
    parser.add_argument(
        "--live-models",
        action="store_true",
        help="Use live models instead of offline clients.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("runs/perf_reports"),
        help="Directory to write markdown + JSON reports (default: runs/perf_reports).",
    )
    parser.add_argument(
        "--telemetry-turns",
        type=int,
        default=10,
        help="How many latest telemetry rows to average for storage KPIs (default: 10).",
    )
    return parser.parse_args()


def build_profile_args(args: argparse.Namespace) -> Namespace:
    """Translate watchdog CLI args into ProfileRun-compatible namespace."""

    return Namespace(
        turns=args.turns,
        choice_id=None,
        random_choice=args.random_choice,
        reset_state=args.reset_state,
        keep_state=args.keep_state,
        tag=args.tag,
        log_level="INFO",
        output=None,
        json=False,
        include_turns=False,
        offline=not args.live_models,
    )


def summarise_agents(report: Dict[str, Any]) -> Tuple[str, float]:
    agents_block = report.get("agents", {}).get("agents", {})
    if not agents_block:
        return "No agent statistics recorded.", 0.0
    lines: List[str] = []
    averages: List[float] = []
    for name in sorted(agents_block):
        stats = agents_block[name]
        lines.append(
            f"- {name}: {stats['calls']} calls | "
            f"avg {stats['avg_s']:.2f}s | p95 {stats['p95_s']:.2f}s | "
            f"failures {stats['failures']}"
        )
        if stats["avg_s"]:
            averages.append(float(stats["avg_s"]))
    fleet_avg = mean(averages) if averages else 0.0
    return "\n".join(lines), fleet_avg


def avg_from_rows(rows: List[Dict[str, str]], key: str) -> float:
    values: List[float] = []
    for row in rows:
        raw = row.get(key)
        if raw is None:
            continue
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return mean(values) if values else 0.0


def build_markdown_report(
    profile_report: Dict[str, Any],
    telemetry_rows: List[Dict[str, str]],
    run_dir: Path,
) -> Tuple[str, Dict[str, Any]]:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    turn_summary = profile_report.get("turn_summary", {})
    agents_md, fleet_avg = summarise_agents(profile_report)
    memory = profile_report.get("memory", {})

    storage_snapshot = avg_from_rows(telemetry_rows, "snapshot_avg_ms")
    storage_persist = avg_from_rows(telemetry_rows, "persist_avg_ms")
    storage_snapshot_p95 = avg_from_rows(telemetry_rows, "snapshot_p95_ms")
    storage_persist_p95 = avg_from_rows(telemetry_rows, "persist_p95_ms")
    telemetry_agent_avg = avg_from_rows(telemetry_rows, "agent_latency_avg")

    summary = {
        "timestamp": timestamp,
        "run_dir": str(run_dir),
        "turns_requested": turn_summary.get("requested"),
        "turns_executed": turn_summary.get("executed"),
        "avg_turn_duration_s": turn_summary.get("avg_duration_s"),
        "max_turn_duration_s": turn_summary.get("max_duration_s"),
        "llm_avg_s": fleet_avg,
        "storage_snapshot_avg_ms": storage_snapshot,
        "storage_snapshot_p95_ms": storage_snapshot_p95,
        "storage_persist_avg_ms": storage_persist,
        "storage_persist_p95_ms": storage_persist_p95,
        "telemetry_agent_latency_avg": telemetry_agent_avg,
        "peak_memory_bytes": memory.get("peak_bytes"),
    }

    md_lines = [
        f"# Fortress Director Performance Report",
        f"- Generated: {timestamp}",
        f"- Run directory: `{run_dir}`",
        "",
        "## Turn Timing",
        f"- Requested turns: {turn_summary.get('requested')}",
        f"- Executed turns: {turn_summary.get('executed')}",
        f"- Average duration: {turn_summary.get('avg_duration_s', 0):.2f}s",
        f"- Max duration: {turn_summary.get('max_duration_s', 0):.2f}s",
        "",
        "## LLM / Agent Latency",
        f"- Fleet average (ProfileRun): {fleet_avg:.2f}s",
        f"- Telemetry agent latency avg: {telemetry_agent_avg:.2f}s",
        agents_md,
        "",
        "## Storage / Persist KPIs",
        f"- Snapshot avg: {storage_snapshot:.1f} ms (p95 {storage_snapshot_p95:.1f} ms)",
        f"- Persist avg: {storage_persist:.1f} ms (p95 {storage_persist_p95:.1f} ms)",
        "",
        "## Memory",
        f"- Peak traced memory: {memory.get('peak_bytes', 0):,} bytes",
    ]
    return "\n".join(md_lines), summary


def main() -> None:
    args = parse_args()
    profile_args = build_profile_args(args)
    profiler = ProfileRun(profile_args)
    profile_report = profiler.execute()
    rows = load_rows(profiler.run_dir, args.telemetry_turns)
    markdown, summary = build_markdown_report(profile_report, rows, profiler.run_dir)

    args.report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    md_path = args.report_dir / f"perf_report_{stamp}.md"
    json_path = args.report_dir / f"perf_report_{stamp}.json"
    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(markdown)
    print(f"\nReport written to {md_path} and {json_path}")


if __name__ == "__main__":
    main()
