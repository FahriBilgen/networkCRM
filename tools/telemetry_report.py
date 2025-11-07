#!/usr/bin/env python3
"""Generate a KPI report over the last N turns."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean
from typing import Dict, List

from tools.telemetry_aggregate import aggregate_runs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarise recent telemetry into a KPI report.",
    )
    parser.add_argument(
        "--run",
        type=Path,
        default=Path("runs/latest_run"),
        help="Run directory (default: runs/latest_run)",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="Number of latest turns to include (default: 10)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional path to write the textual report.",
    )
    return parser.parse_args()


def load_rows(run_dir: Path, limit: int) -> List[Dict[str, str]]:
    csv_path = run_dir / "summary.csv"
    aggregate_runs(run_dir, csv_path)
    rows: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows[-limit:] if limit > 0 else rows


def to_float(row: Dict[str, str], key: str) -> float:
    try:
        return float(row.get(key, 0) or 0)
    except ValueError:
        return 0.0


def build_report(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "No telemetry rows available."
    avg_snapshot = mean(to_float(r, "snapshot_avg_ms") for r in rows)
    avg_persist = mean(to_float(r, "persist_avg_ms") for r in rows)
    avg_agent = mean(to_float(r, "agent_latency_avg") for r in rows)
    glitch_avg = mean(to_float(r, "glitch_roll") for r in rows)
    judge_inconsistent = sum(
        0 if (row.get("judge_consistent", "True") in ("True", "true", "1")) else 1
        for row in rows
    )
    veto_rate = judge_inconsistent / len(rows)
    lines = [
        f"Turns analysed: {len(rows)}",
        f"Snapshot latency avg: {avg_snapshot:.2f} ms",
        f"Persist latency avg: {avg_persist:.2f} ms",
        f"Agent response avg: {avg_agent:.2f} s",
        f"Judge veto rate: {veto_rate*100:.1f}%",
        f"Average glitch roll: {glitch_avg:.1f}",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    rows = load_rows(args.run, args.turns)
    report = build_report(rows)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
