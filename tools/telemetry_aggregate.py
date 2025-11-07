#!/usr/bin/env python3
"""Aggregate run logs into CSV for telemetry analysis."""

import argparse
import csv
import json
from pathlib import Path

FIELDNAMES = [
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
    "fallback_strategy",
    "fallback_summary",
    "guardrail_note_types",
    "snapshot_avg_ms",
    "snapshot_p95_ms",
    "persist_avg_ms",
    "persist_p95_ms",
    "cold_diff_count",
    "cold_diff_bytes",
    "agent_latency_avg",
    "agent_health",
    "judge_consistent",
    "judge_reason",
    "glitch_roll",
]


def _extract_metric(telemetry: dict, op_name: str, key: str) -> float:
    state_io = telemetry.get("state_io_metrics") or {}
    op = state_io.get(op_name) or {}
    value = op.get(key)
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def aggregate_runs(run_dir: Path, output_csv: Path) -> None:
    """Aggregate per-turn JSON payloads into a CSV summary."""

    turn_files = sorted(run_dir.glob("turn_*.json"))
    if not turn_files:
        print("No turn files found in", run_dir)
        return

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writeheader()

        for turn_file in turn_files:
            try:
                data = json.loads(turn_file.read_text(encoding="utf-8"))
                event = data.get("event", {}) or {}
                telemetry = data.get("telemetry", {}) or {}

                motif_injected = event.get("motif_injected")
                guardrail_notes = telemetry.get("guardrail_notes") or data.get(
                    "guardrail_notes", []
                )
                guardrail_types = []
                if isinstance(guardrail_notes, list):
                    guardrail_types = [
                        str(note.get("type", "")).strip()
                        for note in guardrail_notes
                        if isinstance(note, dict)
                    ]
                guardrail_types_str = ",".join(
                    sorted({note for note in guardrail_types if note})
                )

                agent_metrics = telemetry.get("agents") or {}
                agent_latency = [
                    entry.get("average_response_time", 0.0)
                    for entry in agent_metrics.values()
                    if isinstance(entry, dict)
                ]
                avg_agent_latency = (
                    sum(agent_latency) / len(agent_latency) if agent_latency else 0.0
                )

                judge_info = telemetry.get("judge") or data.get(
                    "previous_judge_verdict", {}
                )
                glitch_snapshot = telemetry.get("glitch_snapshot") or data.get(
                    "glitch", {}
                )

                metrics = data.get("metrics_after", {}) or {}

                row = {
                    "turn": data.get("turn", 0),
                    "motif_injected": bool(motif_injected),
                    "motif_text": motif_injected or "",
                    "motif_origin": "llm" if motif_injected else "",
                    "motif_remaining": event.get("motif_persist_for", 0),
                    "judge_veto": not judge_info.get("consistent", True),
                    "veto_reason": judge_info.get("reason", ""),
                    "major_event": event.get("major_event", False),
                    "safe_function_executions": len(
                        data.get("safe_function_results", [])
                    ),
                    "order": metrics.get("order", 0),
                    "morale": metrics.get("morale", 0),
                    "resources": metrics.get("resources", 0),
                    "knowledge": metrics.get("knowledge", 0),
                    "corruption": metrics.get("corruption", 0),
                    "glitch": metrics.get("glitch", 0),
                    "fallback_strategy": telemetry.get("fallback_strategy")
                    or data.get("fallback_context", {}).get("strategy"),
                    "fallback_summary": telemetry.get("fallback_summary")
                    or data.get("fallback_summary"),
                    "guardrail_note_types": guardrail_types_str,
                    "snapshot_avg_ms": _extract_metric(telemetry, "snapshot", "avg_ms"),
                    "snapshot_p95_ms": _extract_metric(telemetry, "snapshot", "p95_ms"),
                    "persist_avg_ms": _extract_metric(telemetry, "persist", "avg_ms"),
                    "persist_p95_ms": _extract_metric(telemetry, "persist", "p95_ms"),
                    "cold_diff_count": telemetry.get("cold_diff_stats", {}).get(
                        "count", 0
                    ),
                    "cold_diff_bytes": telemetry.get("cold_diff_stats", {}).get(
                        "bytes", 0.0
                    ),
                    "agent_latency_avg": avg_agent_latency,
                    "agent_health": telemetry.get("agent_system_health"),
                    "judge_consistent": judge_info.get("consistent", True),
                    "judge_reason": judge_info.get("reason", ""),
                    "glitch_roll": glitch_snapshot.get("roll", 0),
                }
                writer.writerow(row)
            except Exception as exc:
                print(f"Error processing {turn_file}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate Fortress Director run telemetry.",
    )
    parser.add_argument(
        "--run",
        type=Path,
        default=Path("runs/latest_run"),
        help="Run directory containing turn_XXX.json files.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("runs/latest_run/summary.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()
    aggregate_runs(args.run, args.out)
    print(f"Telemetry aggregated to {args.out}")


if __name__ == "__main__":
    main()
