#!/usr/bin/env python3
"""Telemetry script to analyze Fortress Director logs and extract metrics."""

import json
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict, Counter


def parse_log_file(log_path: Path) -> List[Dict[str, Any]]:
    """Parse a log file and extract structured events."""
    events = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            # Parse log lines like: 2024-01-01 12:00:00 INFO fortress_director.orchestrator: Event occurred
            match = re.match(
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+) ([^:]+): (.+)",
                line.strip(),
            )
            if match:
                timestamp, level, logger, message = match.groups()
                events.append(
                    {
                        "timestamp": timestamp,
                        "level": level,
                        "logger": logger,
                        "message": message,
                    }
                )
    return events


def extract_metrics_from_logs(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract key metrics from parsed log events."""
    metrics = {
        "total_turns": 0,
        "judge_vetoes": 0,
        "creativity_fallbacks": 0,
        "major_events": 0,
        "repetition_warnings": 0,
        "error_count": 0,
        "agent_response_times": [],
        "scene_repetitions": 0,
        "motif_injections": 0,
    }

    turn_pattern = re.compile(r"turn (\d+)")
    veto_pattern = re.compile(r"Judge.*veto|inconsistent")
    fallback_pattern = re.compile(r"fallback|LLM failed")
    major_pattern = re.compile(r"major_event|major incident")
    repetition_pattern = re.compile(r"repetition|loop|stagnation")
    error_pattern = re.compile(r"ERROR|Exception")
    response_time_pattern = re.compile(r"response time: (\d+\.?\d*)s")
    scene_rep_pattern = re.compile(r"same scene|scene repetition")
    motif_pattern = re.compile(r"motif.*inject")

    for event in events:
        message = event["message"].lower()

        if turn_pattern.search(message):
            match = turn_pattern.search(event["message"])
            if match:
                turn_num = int(match.group(1))
                metrics["total_turns"] = max(metrics["total_turns"], turn_num)

        if veto_pattern.search(message):
            metrics["judge_vetoes"] += 1

        if fallback_pattern.search(message):
            metrics["creativity_fallbacks"] += 1

        if major_pattern.search(message):
            metrics["major_events"] += 1

        if repetition_pattern.search(message):
            metrics["repetition_warnings"] += 1

        if error_pattern.search(message):
            metrics["error_count"] += 1

        if response_time_pattern.search(event["message"]):
            match = response_time_pattern.search(event["message"])
            if match:
                time_val = float(match.group(1))
                metrics["agent_response_times"].append(time_val)

        if scene_rep_pattern.search(message):
            metrics["scene_repetitions"] += 1

        if motif_pattern.search(message):
            metrics["motif_injections"] += 1

    # Calculate averages
    if metrics["agent_response_times"]:
        metrics["avg_response_time"] = sum(metrics["agent_response_times"]) / len(
            metrics["agent_response_times"]
        )
    else:
        metrics["avg_response_time"] = 0

    return metrics


def generate_report(metrics: Dict[str, Any], output_path: Path) -> None:
    """Generate a telemetry report."""
    report = f"""# Fortress Director Telemetry Report

## Summary
- Total Turns: {metrics['total_turns']}
- Judge Vetoes: {metrics['judge_vetoes']}
- Creativity Fallbacks: {metrics['creativity_fallbacks']}
- Major Events: {metrics['major_events']}
- Repetition Warnings: {metrics['repetition_warnings']}
- Errors: {metrics['error_count']}
- Average Agent Response Time: {metrics['avg_response_time']:.2f}s
- Scene Repetitions: {metrics['scene_repetitions']}
- Motif Injections: {metrics['motif_injections']}

## Analysis
"""

    # Add analysis based on metrics
    if metrics["judge_vetoes"] > metrics["total_turns"] * 0.1:
        report += "- High judge veto rate detected. Consider adjusting JUDGE_BASE_VETO_PROB.\n"

    if metrics["creativity_fallbacks"] > 0:
        report += f"- {metrics['creativity_fallbacks']} creativity fallbacks occurred. LLM reliability may need improvement.\n"

    if metrics["repetition_warnings"] > metrics["total_turns"] * 0.05:
        report += "- Frequent repetition warnings. Check diversity mechanisms.\n"

    if metrics["error_count"] > 0:
        report += f"- {metrics['error_count']} errors logged. Review error handling.\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)


def main():
    """Main entry point for telemetry analysis."""
    log_dir = Path("logs")
    if not log_dir.exists():
        print("No logs directory found.")
        return

    # Find the latest log file
    log_files = list(log_dir.glob("*.log"))
    if not log_files:
        print("No log files found.")
        return

    latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
    print(f"Analyzing log file: {latest_log}")

    events = parse_log_file(latest_log)
    metrics = extract_metrics_from_logs(events)

    report_path = Path("telemetry_report.md")
    generate_report(metrics, report_path)
    print(f"Report generated: {report_path}")


if __name__ == "__main__":
    main()
