#!/usr/bin/env python3
"""Summarise recent performance reports and suggest backlog actions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Dict, List

THRESHOLDS = {
    "avg_turn_duration_s": 60.0,
    "storage_snapshot_p95_ms": 50.0,
    "storage_persist_p95_ms": 50.0,
    "telemetry_agent_latency_avg": 5.0,
    "peak_memory_bytes": 250 * 1024 * 1024,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a telemetry retro over recent performance reports.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("runs/perf_reports"),
        help="Directory containing perf_report_*.json files (default: runs/perf_reports).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="How many recent reports to include (default: 5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("runs/maintenance"),
        help="Directory to store the retro summary (default: runs/maintenance).",
    )
    return parser.parse_args()


def load_reports(report_dir: Path, limit: int) -> List[Dict[str, float]]:
    reports: List[Dict[str, float]] = []
    if not report_dir.exists():
        return reports
    files = sorted(report_dir.glob("perf_report_*.json"), reverse=True)
    for file in files[:limit]:
        try:
            reports.append(json.loads(file.read_text(encoding="utf-8")))
        except Exception:
            continue
    return reports


def compute_averages(reports: List[Dict[str, float]]) -> Dict[str, float]:
    if not reports:
        return {}
    keys = {
        "avg_turn_duration_s",
        "storage_snapshot_avg_ms",
        "storage_snapshot_p95_ms",
        "storage_persist_avg_ms",
        "storage_persist_p95_ms",
        "telemetry_agent_latency_avg",
        "peak_memory_bytes",
    }
    averages: Dict[str, float] = {}
    for key in keys:
        values = [report.get(key) for report in reports if report.get(key) is not None]
        if values:
            averages[key] = mean(values)
    return averages


def build_backlog(averages: Dict[str, float]) -> List[str]:
    backlog: List[str] = []
    for key, threshold in THRESHOLDS.items():
        value = averages.get(key)
        if value is None:
            continue
        if value > threshold:
            backlog.append(
                f"- Investigate metric `{key}` avg={value:.2f} (threshold {threshold})."
            )
    if not backlog:
        backlog.append("- No KPI regressions detected; keep monitoring.")
    return backlog


def main() -> None:
    args = parse_args()
    reports = load_reports(args.reports_dir, args.limit)
    if not reports:
        print("No perf_report_*.json files found; run tools/perf_watchdog.py first.")
        return
    averages = compute_averages(reports)
    backlog = build_backlog(averages)

    args.output.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    md_path = args.output / f"telemetry_retro_{timestamp}.md"
    lines = [
        f"# Telemetry Retro ({timestamp})",
        f"- Source dir: `{args.reports_dir}`",
        f"- Reports analysed: {len(reports)}",
        "",
        "## Metric Averages",
    ]
    for key, value in sorted(averages.items()):
        lines.append(f"- {key}: {value:.2f}")
    lines.append("")
    lines.append("## Recommended Backlog Items")
    lines.extend(backlog)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Telemetry retro written to {md_path}")


if __name__ == "__main__":
    main()
