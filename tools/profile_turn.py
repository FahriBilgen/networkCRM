#!/usr/bin/env python3
"""Profile orchestrator turns and collect core performance metrics."""

from __future__ import annotations

import argparse
import json
import logging
import time
import tracemalloc
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fortress_director.orchestrator.orchestrator import (
    DEFAULT_WORLD_STATE,
    Orchestrator,
)
from fortress_director.settings import SETTINGS
from utils.agent_monitor import (
    AGENT_MONITOR,
    reset_agent_monitor,
)
from fortress_director.utils.logging_config import configure_logging

try:  # pragma: no cover - optional dependency in some environments
    from fortress_director.llm.offline_client import OfflineOllamaClient
except ImportError:  # pragma: no cover - fallback when stub is absent
    OfflineOllamaClient = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

DEFAULT_SILENCED_LOGGERS = {
    "fortress_director.agents": "WARNING",
    "fortress_director.codeaware.function_validator": "INFO",
    "fortress_director.utils.metrics_manager": "INFO",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a turn with instrumentation and emit profiling data.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=1,
        help="Number of sequential turns to execute (default: 1).",
    )
    parser.add_argument(
        "--choice-id",
        help="Optional player choice id to commit each turn.",
    )
    parser.add_argument(
        "--random-choice",
        action="store_true",
        help="Request the orchestrator to pick a random option per turn.",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset world state to defaults before profiling.",
    )
    parser.add_argument(
        "--keep-state",
        action="store_true",
        help="Keep mutated world state instead of restoring the initial snapshot.",
    )
    parser.add_argument(
        "--tag",
        help="Optional suffix for the profiling run directory.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Console log level (default: INFO).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path to write the profiling report as JSON.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the profiling report as JSON to stdout.",
    )
    parser.add_argument(
        "--include-turns",
        action="store_true",
        help="Include per-turn diagnostics in the JSON report.",
    )
    parser.add_argument(
        "--use-live-models",
        dest="offline",
        action="store_false",
        help="Use configured live models instead of offline stubs.",
    )
    parser.set_defaults(offline=True)
    return parser.parse_args()


def percentile(values: List[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round(quantile * (len(ordered) - 1)))
    idx = max(0, min(idx, len(ordered) - 1))
    return ordered[idx]


def format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if abs(size) < 1024.0 or unit == units[-1]:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}B"


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                entries.append(json.loads(text))
            except json.JSONDecodeError:
                LOGGER.warning("Skipping malformed JSON line in %s", path)
    return entries


def file_stats(path: Path, count_lines: bool = False) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
    }
    if not path.exists():
        info["bytes"] = 0
        return info
    info["bytes"] = path.stat().st_size
    if count_lines:
        lines = 0
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for _ in handle:
                lines += 1
        info["lines"] = lines
    return info


class ProfileRun:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        tag = args.tag or f"profile_{timestamp}"
        self.run_dir = (SETTINGS.project_root / "runs" / tag).resolve()
        self.turn_records: List[Dict[str, Any]] = []
        self.turn_durations: List[float] = []
        self.log_path: Optional[Path] = None
        self.initial_state: Optional[Dict[str, Any]] = None

    def execute(self) -> Dict[str, Any]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        quiet_loggers = dict(DEFAULT_SILENCED_LOGGERS)
        log_target = self._derive_log_path()
        self.log_path = configure_logging(
            console_level=self.args.log_level,
            file_level="DEBUG",
            log_path=log_target,
            quiet_loggers=quiet_loggers,
            force=True,
        )
        reset_agent_monitor()
        AGENT_MONITOR.monitoring_enabled = True
        tracemalloc.start()
        current_mem = peak_mem = 0
        orchestrator = self._build_orchestrator()
        try:
            self._profile(orchestrator)
            current_mem, peak_mem = tracemalloc.get_traced_memory()
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()
        report = self._compile_report()
        report["memory"] = {
            "current_bytes": current_mem,
            "peak_bytes": peak_mem,
        }
        if not self.args.keep_state and self.initial_state is not None:
            orchestrator.state_store.persist(self.initial_state)
        return report

    def _derive_log_path(self) -> Path:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return self.run_dir / f"profile_{stamp}.log"

    def _build_orchestrator(self) -> Orchestrator:
        orchestrator = Orchestrator.build_default()
        try:
            orchestrator.runs_dir = self.run_dir
        except Exception:  # pragma: no cover - defensive guard
            LOGGER.debug("Unable to override orchestrator.run_dir", exc_info=True)
        self.initial_state = orchestrator.state_store.snapshot()
        if self.args.reset_state:
            orchestrator.state_store.persist(deepcopy(DEFAULT_WORLD_STATE))
        if self.args.offline:
            self._swap_offline_clients(orchestrator)
        return orchestrator

    def _swap_offline_clients(self, orchestrator: Orchestrator) -> None:
        if OfflineOllamaClient is None:
            LOGGER.warning(
                "OfflineOllamaClient unavailable; continuing with live models.",
            )
            return
        mappings = [
            ("event_agent", "event"),
            ("world_agent", "world"),
            ("creativity_agent", "creativity"),
            ("planner_agent", "planner"),
            ("director_agent", "director"),
            ("character_agent", "character"),
            ("judge_agent", "judge"),
        ]
        for attr, key in mappings:
            agent = getattr(orchestrator, attr, None)
            if agent is not None and hasattr(agent, "_client"):
                agent._client = OfflineOllamaClient(agent_key=key)

    def _profile(self, orchestrator: Orchestrator) -> None:
        turn_budget = max(1, self.args.turns)
        for turn_index in range(turn_budget):
            choice_id = self._resolve_choice()
            start = time.perf_counter()
            result = orchestrator.run_turn(player_choice_id=choice_id)
            elapsed = time.perf_counter() - start
            self.turn_durations.append(elapsed)
            state_after = orchestrator.state_store.snapshot()
            turn_number = int(state_after.get("turn", turn_index + 1) or (turn_index + 1))
            self._record_turn(turn_number, elapsed, result, state_after)
            self._write_turn_snapshot(turn_number, result)
            if result.get("win_loss", {}).get("status") != "ongoing":
                break

    def _resolve_choice(self) -> Optional[str]:
        if self.args.random_choice:
            return "__random__"
        if self.args.choice_id:
            return self.args.choice_id
        return None

    def _record_turn(
        self,
        turn_number: int,
        duration: float,
        result: Dict[str, Any],
        state_after: Dict[str, Any],
    ) -> None:
        telemetry = result.get("telemetry") or {}
        record = {
            "turn": turn_number,
            "duration_s": duration,
            "judge_verdict": state_after.get("previous_judge_verdict", {}),
            "safe_functions": result.get("safe_function_results", []),
            "guardrails": telemetry.get("safe_function_guardrails", {}),
            "win_loss": result.get("win_loss", {}),
        }
        fallback_context = result.get("fallback_context")
        if isinstance(fallback_context, dict) and fallback_context:
            record["fallback_context"] = fallback_context
        if self.args.include_turns:
            record["telemetry"] = telemetry
            record["options"] = result.get("options", [])
        self.turn_records.append(record)

    def _write_turn_snapshot(self, turn_number: int, payload: Dict[str, Any]) -> None:
        target = self.run_dir / f"turn_{turn_number:03d}.json"
        target.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _turn_summary(self) -> Dict[str, Any]:
        executed = len(self.turn_durations)
        total = sum(self.turn_durations)
        average = total / executed if executed else 0.0
        return {
            "requested": self.args.turns,
            "executed": executed,
            "total_duration_s": total,
            "avg_duration_s": average,
            "min_duration_s": min(self.turn_durations) if executed else 0.0,
            "max_duration_s": max(self.turn_durations) if executed else 0.0,
            "stopped_early": executed < self.args.turns,
        }

    def _agent_metrics(self) -> Dict[str, Any]:
        agents: Dict[str, Dict[str, Any]] = {}
        for name, metrics in AGENT_MONITOR.metrics.items():
            durations = list(metrics.response_times)
            agents[name] = {
                "calls": len(durations),
                "avg_s": metrics.average_response_time,
                "p95_s": percentile(durations, 0.95),
                "max_s": max(durations) if durations else 0.0,
                "successes": metrics.success_count,
                "failures": metrics.failure_count,
                "consistency_violations": metrics.consistency_violations,
                "quality_issues": metrics.quality_issues,
            }
        health = AGENT_MONITOR.get_performance_report()["system_health"]
        return {"system_health": health, "agents": agents}

    def _judge_metrics(self) -> Dict[str, Any]:
        total = vetoes = 0
        reasons: Counter[str] = Counter()
        penalties: Counter[str] = Counter()
        for record in self.turn_records:
            verdict = record.get("judge_verdict") or {}
            if not verdict:
                continue
            total += 1
            consistent = bool(verdict.get("consistent", True))
            if not consistent:
                vetoes += 1
                reason = verdict.get("reason")
                if isinstance(reason, str) and reason.strip():
                    reasons[reason.strip()] += 1
            penalty = verdict.get("penalty") or verdict.get("penalty_applied")
            if isinstance(penalty, str) and penalty and penalty != "none":
                penalties[penalty] += 1
        rate = vetoes / total if total else 0.0
        return {
            "verdicts": total,
            "vetoes": vetoes,
            "veto_rate": rate,
            "top_reasons": reasons.most_common(5),
            "penalties": penalties.most_common(5),
        }

    def _safe_function_metrics(self) -> Dict[str, Any]:
        executed = successes = failures = 0
        calls: Counter[str] = Counter()
        failed_calls: Counter[str] = Counter()
        for record in self.turn_records:
            for entry in record.get("safe_functions") or []:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("name", "unknown"))
                calls[name] += 1
                executed += 1
                if entry.get("success", False):
                    successes += 1
                else:
                    failures += 1
                    failed_calls[name] += 1
        failure_rate = failures / executed if executed else 0.0
        audit_path = self.run_dir / "audit.jsonl"
        rejection_reasons: Counter[str] = Counter()
        if audit_path.exists():
            for entry in read_jsonl(audit_path):
                if entry.get("applied", False):
                    continue
                reasons = entry.get("reasons") or []
                if reasons:
                    for reason in reasons:
                        if isinstance(reason, str) and reason.strip():
                            rejection_reasons[reason.strip()] += 1
                else:
                    rejection_reasons["unspecified"] += 1
        return {
            "executed": executed,
            "successes": successes,
            "failures": failures,
            "failure_rate": failure_rate,
            "top_calls": calls.most_common(5),
            "top_failure_calls": failed_calls.most_common(5),
            "rejection_reasons": rejection_reasons.most_common(5),
            "audit_path": str(audit_path) if audit_path.exists() else None,
        }

    def _artifact_metrics(self) -> Dict[str, Any]:
        artifacts = {
            "world_state_json": file_stats(SETTINGS.world_state_path),
            "world_state_sqlite": file_stats(SETTINGS.db_path),
            "audit_jsonl": file_stats(self.run_dir / "audit.jsonl", count_lines=True),
            "replay_jsonl": file_stats(self.run_dir / "replay.jsonl", count_lines=True),
        }
        if self.log_path:
            artifacts["profile_log"] = file_stats(self.log_path, count_lines=True)
        artifacts["run_dir"] = str(self.run_dir)
        return artifacts

    def _compile_report(self) -> Dict[str, Any]:
        report = {
            "run_dir": str(self.run_dir),
            "log_file": str(self.log_path) if self.log_path else None,
            "turn_summary": self._turn_summary(),
            "agents": self._agent_metrics(),
            "judge": self._judge_metrics(),
            "safe_functions": self._safe_function_metrics(),
            "artifacts": self._artifact_metrics(),
        }
        if self.args.include_turns:
            report["turns"] = self.turn_records
        return report


def format_summary(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    turn_summary = report["turn_summary"]
    lines.append(f"Run directory: {report['run_dir']}")
    log_file = report.get("log_file")
    if log_file:
        lines.append(f"Log file: {log_file}")
    lines.append(
        f"Turns executed: {turn_summary['executed']} "
        f"(requested {turn_summary['requested']})",
    )
    lines.append(
        "Turn durations: "
        f"avg {turn_summary['avg_duration_s']:.2f}s | "
        f"min {turn_summary['min_duration_s']:.2f}s | "
        f"max {turn_summary['max_duration_s']:.2f}s",
    )
    agent_block = report["agents"]["agents"]
    if agent_block:
        lines.append("LLM call stats:")
        for agent_name in sorted(agent_block):
            stats = agent_block[agent_name]
            lines.append(
                f"  {agent_name}: {stats['calls']} calls, "
                f"avg {stats['avg_s']:.2f}s, p95 {stats['p95_s']:.2f}s, "
                f"failures {stats['failures']}",
            )
    judge = report["judge"]
    if judge["verdicts"]:
        lines.append(
            f"Judge veto rate: {judge['veto_rate']*100:.1f}% "
            f"({judge['vetoes']}/{judge['verdicts']})",
        )
        top_reasons = ", ".join(
            f"{reason} ({count})" for reason, count in judge["top_reasons"]
        )
        if top_reasons:
            lines.append(f"  Top veto reasons: {top_reasons}")
    safe = report["safe_functions"]
    if safe["executed"]:
        lines.append(
            f"Safe functions: {safe['executed']} calls, "
            f"failure rate {safe['failure_rate']*100:.1f}%",
        )
        top_failures = ", ".join(
            f"{name} ({count})" for name, count in safe["top_failure_calls"]
        )
        if top_failures:
            lines.append(f"  Frequent failures: {top_failures}")
        top_rejections = ", ".join(
            f"{reason} ({count})" for reason, count in safe["rejection_reasons"]
        )
        if top_rejections:
            lines.append(f"  Validator rejections: {top_rejections}")
    artifacts = report["artifacts"]
    world_json = artifacts["world_state_json"]
    lines.append(
        "World state: "
        f"{format_bytes(world_json['bytes'])} JSON | "
        f"{format_bytes(artifacts['world_state_sqlite']['bytes'])} SQLite",
    )
    log_info = artifacts.get("profile_log")
    if log_info and log_info.get("exists"):
        lines.append(
            f"Profile log size: {format_bytes(log_info['bytes'])} "
            f"({log_info.get('lines', 0)} lines)",
        )
    memory = report.get("memory", {})
    peak_bytes = memory.get("peak_bytes", 0)
    if peak_bytes:
        lines.append(f"Peak traced memory: {format_bytes(int(peak_bytes))}")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    profiler = ProfileRun(args)
    report = profiler.execute()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_summary(report))


if __name__ == "__main__":
    main()
