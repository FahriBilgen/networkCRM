#!/usr/bin/env python3
"""Build a KPI digest that pairs perf_watchdog output with telemetry stats."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

from tools.telemetry_report import build_report, load_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine perf_watchdog output with telemetry KPIs.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("runs/perf_reports/ci"),
        help="Directory that stores perf_report_<stamp> files (default: runs/perf_reports/ci).",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=20,
        help="Number of telemetry turns to summarise (default: 20).",
    )
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("runs/perf_reports/ci/kpi_summary.md"),
        help="Where to write the combined KPI markdown (default: runs/perf_reports/ci/kpi_summary.md).",
    )
    return parser.parse_args()


def find_latest_report(report_dir: Path) -> Path:
    json_reports: List[Path] = sorted(report_dir.glob("perf_report_*.json"))
    if not json_reports:
        raise FileNotFoundError(
            f"No perf_report_*.json files found under {report_dir}. "
            "Make sure tools/perf_watchdog.py ran first.",
        )
    return max(json_reports)


def main() -> None:
    args = parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)
    latest_json = find_latest_report(args.report_dir)
    payload = json.loads(latest_json.read_text(encoding="utf-8"))
    run_dir = Path(payload.get("run_dir", "runs/latest_run"))
    perf_md_path = latest_json.with_suffix(".md")
    perf_md = (
        perf_md_path.read_text(encoding="utf-8")
        if perf_md_path.exists()
        else "Perf watchdog markdown missing."
    )

    telemetry_text = "No telemetry rows available."
    if run_dir.exists():
        try:
            rows = load_rows(run_dir, args.turns)
            telemetry_text = build_report(rows)
        except Exception as exc:  # pragma: no cover - defensive guard
            telemetry_text = f"Telemetry summary failed: {exc}"
    else:
        telemetry_text = f"Run directory {run_dir} does not exist."

    summary_lines = [
        "# Weekly KPI Summary",
        "",
        "## Perf Watchdog Snapshot",
        perf_md.strip(),
        "",
        f"## Telemetry Window (last {args.turns} turns)",
        telemetry_text.strip(),
        "",
        f"_Artifacts generated from {latest_json.name}_",
    ]
    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    args.summary_path.write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )
    print(f"Summary written to {args.summary_path}")


if __name__ == "__main__":
    main()
