#!/usr/bin/env python3
"""Aggregate run logs into CSV for telemetry analysis."""

import argparse
import csv
import json
from pathlib import Path


def aggregate_runs(run_dir: Path, output_csv: Path) -> None:
    """Aggregate turn data from runs/latest_run into CSV."""
    turn_files = sorted(run_dir.glob("turn_*.json"))
    if not turn_files:
        print("No turn files found in", run_dir)
        return

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = [
            "turn",
            "motif_injected",
            "motif_text",
            "motif_origin",
            "motif_remaining",
            "judge_veto",
            "veto_reason",
            "major_event",
            "safe_function_executions",
            "order",
            "morale",
            "resources",
            "knowledge",
            "corruption",
            "glitch",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for turn_file in turn_files:
            try:
                data = json.loads(turn_file.read_text(encoding="utf-8"))
                turn = data.get("turn", 0)
                event = data.get("event", {})
                motif_injected = event.get("motif_injected")
                motif_text = motif_injected or ""
                motif_origin = "llm" if motif_injected else ""
                motif_remaining = event.get("motif_persist_for", 0)
                judge_verdict = data.get("previous_judge_verdict", {})
                judge_veto = not judge_verdict.get("consistent", True)
                veto_reason = judge_verdict.get("reason", "")
                major_event = event.get("major_event", False)
                safe_execs = len(data.get("safe_function_results", []))
                metrics = data.get("metrics_after", {})
                row = {
                    "turn": turn,
                    "motif_injected": bool(motif_injected),
                    "motif_text": motif_text,
                    "motif_origin": motif_origin,
                    "motif_remaining": motif_remaining,
                    "judge_veto": judge_veto,
                    "veto_reason": veto_reason,
                    "major_event": major_event,
                    "safe_function_executions": safe_execs,
                    "order": metrics.get("order", 0),
                    "morale": metrics.get("morale", 0),
                    "resources": metrics.get("resources", 0),
                    "knowledge": metrics.get("knowledge", 0),
                    "corruption": metrics.get("corruption", 0),
                    "glitch": metrics.get("glitch", 0),
                }
                writer.writerow(row)
            except Exception as e:
                print(f"Error processing {turn_file}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate Fortress Director run telemetry."
    )
    parser.add_argument(
        "--run", type=Path, default=Path("runs/latest_run"), help="Run directory"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("runs/latest_run/summary.csv"),
        help="Output CSV",
    )
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    aggregate_runs(args.run, args.out)
    print(f"Telemetry aggregated to {args.out}")


if __name__ == "__main__":
    main()
