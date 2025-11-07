#!/usr/bin/env python3
"""Measure snapshot/persist performance for the Fortress Director state store."""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
import tempfile
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fortress_director.orchestrator.orchestrator import StateStore
from fortress_director.settings import DEFAULT_WORLD_STATE, SETTINGS


def _readable_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if abs(size) < 1024.0 or unit == units[-1]:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}B"


def _stats(samples: Iterable[float]) -> Dict[str, float]:
    data = list(samples)
    if not data:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "median_ms": 0.0,
            "p95_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
        }
    ordered = sorted(data)
    return {
        "count": len(data),
        "avg_ms": statistics.mean(data),
        "median_ms": statistics.median(data),
        "p95_ms": ordered[int(0.95 * (len(ordered) - 1))],
        "min_ms": ordered[0],
        "max_ms": ordered[-1],
    }


def _copy_state_files(target_dir: Path, state_path: Path | None, db_path: Path | None) -> Tuple[Path, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    sandbox_state = target_dir / "world_state.json"
    sandbox_db = target_dir / "game_state.sqlite"

    source_state = state_path or SETTINGS.world_state_path
    if source_state.exists():
        shutil.copy2(source_state, sandbox_state)
    else:
        sandbox_state.write_text(json.dumps(DEFAULT_WORLD_STATE, indent=2), encoding="utf-8")

    source_db = db_path or SETTINGS.db_path
    if source_db.exists():
        shutil.copy2(source_db, sandbox_db)
    else:
        sandbox_db.write_bytes(b"")
    return sandbox_state, sandbox_db


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Profile StateStore snapshot/persist latency.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=50,
        help="Number of measured iterations per operation (default: 50).",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=5,
        help="Warm-up calls per operation that are not measured (default: 5).",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        help="Custom world_state.json path to profile (default: SETTINGS.world_state_path).",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Custom SQLite path to profile (default: SETTINGS.db_path).",
    )
    parser.add_argument(
        "--use-live-state",
        action="store_true",
        help="Operate on the provided paths in-place instead of copying to a sandbox.",
    )
    parser.add_argument(
        "--keep-mutations",
        action="store_true",
        help="When --use-live-state is set, keep the final state instead of restoring the original snapshot.",
    )
    parser.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="Keep the temporary sandbox directory for inspection.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON instead of a human summary.",
    )
    parser.add_argument(
        "--mode",
        choices=("full", "hot"),
        default="full",
        help="Snapshot mode to measure (full or hot layer only).",
    )
    return parser.parse_args()


class StateIOProfiler:
    """Utility to benchmark snapshot/persist."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.temp_dir: Path | None = None
        self.state_path: Path
        self.db_path: Path
        self._sandbox_note = ""
        self._configure_paths()

    def _configure_paths(self) -> None:
        if self.args.use_live_state:
            self.state_path = (self.args.state_path or SETTINGS.world_state_path).resolve()
            self.db_path = (self.args.db_path or SETTINGS.db_path).resolve()
            self._original_state: Dict[str, Any] | None = None
            self._sandbox_note = "using live state"
        else:
            tmp_root = Path(tempfile.mkdtemp(prefix="state_io_profile_"))
            self.temp_dir = tmp_root
            state_path, db_path = _copy_state_files(
                tmp_root,
                self.args.state_path,
                self.args.db_path,
            )
            self.state_path = state_path
            self.db_path = db_path
            self._sandbox_note = f"sandbox={tmp_root}"

    def _time_call(self, fn, iterations: int, warmup: int) -> List[float]:
        for _ in range(max(0, warmup)):
            fn()
        samples: List[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            duration_ms = (time.perf_counter() - start) * 1000.0
            samples.append(duration_ms)
        return samples

    def _persist_callable(self, store: StateStore, base: Dict[str, Any]) -> List[float]:
        iteration_marker = {"_profile_ts": time.time()}

        def run_once(counter: int) -> None:
            payload = deepcopy(base)
            payload.setdefault("_profile", {})["persist_iteration"] = counter
            payload["_profile_metadata"] = iteration_marker
            store.persist(payload)

        warmup = max(0, self.args.warmup)
        iterations = max(1, self.args.iterations)
        for i in range(warmup):
            run_once(i)
        samples: List[float] = []
        for i in range(iterations):
            start = time.perf_counter()
            run_once(i + warmup)
            samples.append((time.perf_counter() - start) * 1000.0)
        return samples

    def profile(self) -> Dict[str, Any]:
        store = StateStore(self.state_path, db_path=self.db_path)
        if self.args.use_live_state and not self.args.keep_mutations:
            self._original_state = store.snapshot()
        snapshot_callable = store.snapshot
        if getattr(self.args, "mode", "full") == "hot":
            snapshot_callable = store.snapshot_hot
        snapshot_samples = self._time_call(
            snapshot_callable,
            iterations=max(1, self.args.iterations),
            warmup=max(0, self.args.warmup),
        )
        state_baseline = store.snapshot()
        persist_samples = self._persist_callable(store, state_baseline)

        if self.args.use_live_state and not self.args.keep_mutations and self._original_state is not None:
            store.persist(self._original_state)

        report = {
            "state_path": str(self.state_path),
            "db_path": str(self.db_path),
            "sandbox": self._sandbox_note,
            "iterations": max(1, self.args.iterations),
            "warmup": max(0, self.args.warmup),
            "mode": getattr(self.args, "mode", "full"),
            "snapshot_ms": _stats(snapshot_samples),
            "persist_ms": _stats(persist_samples),
            "artifacts": {
                "world_state_json": self._file_info(self.state_path),
                "world_state_sqlite": self._file_info(self.db_path),
            },
        }
        self._cleanup()
        return report

    def _cleanup(self) -> None:
        if self.temp_dir and not self.args.keep_sandbox:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _file_info(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {"path": str(path), "exists": False, "size_bytes": 0, "size_human": "0B"}
        size = path.stat().st_size
        return {
            "path": str(path),
            "exists": True,
            "size_bytes": size,
            "size_human": _readable_bytes(size),
        }


def format_summary(report: Dict[str, Any]) -> str:
    lines = [
        f"State path: {report['state_path']}",
        f"SQLite path: {report['db_path']}",
        f"Context: {report['sandbox']}",
        f"Iterations: {report['iterations']} (warmup={report['warmup']}, mode={report.get('mode','full')})",
        "",
        "*** Snapshot ***",
        _format_stats(report["snapshot_ms"]),
        "",
        "*** Persist ***",
        _format_stats(report["persist_ms"]),
        "",
        "Artifacts:",
    ]
    for key, info in report["artifacts"].items():
        lines.append(
            f"  - {key}: {info.get('size_human')} ({info.get('size_bytes')} bytes) -> {info.get('path')}",
        )
    return "\n".join(lines)


def _format_stats(stats_dict: Dict[str, float]) -> str:
    return (
        f"count={stats_dict['count']} | "
        f"avg={stats_dict['avg_ms']:.2f}ms | "
        f"median={stats_dict['median_ms']:.2f}ms | "
        f"p95={stats_dict['p95_ms']:.2f}ms | "
        f"min={stats_dict['min_ms']:.2f}ms | "
        f"max={stats_dict['max_ms']:.2f}ms"
    )


def main() -> None:
    args = parse_args()
    profiler = StateIOProfiler(args)
    report = profiler.profile()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(format_summary(report))


if __name__ == "__main__":
    main()

