#!/usr/bin/env python3
"""Audit requirements*.txt files and logging level usage."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "runs",
    "logs",
    "tmp",
    "data",
    "__pycache__",
    ".benchmarks",
}
LOG_LEVEL_PATTERN = re.compile(r"setLevel\(\s*logging\.([A-Z]+)\s*\)")
IMPORT_PATTERN = re.compile(r"^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan requirements files and logging usage.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/maintenance"),
        help="Directory to store the audit report (default: runs/maintenance).",
    )
    return parser.parse_args()


def list_requirements() -> Dict[str, Set[str]]:
    req_map: Dict[str, Set[str]] = defaultdict(set)
    for req_file in PROJECT_ROOT.glob("requirements*.txt"):
        for raw_line in req_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            package = re.split(r"[=<>! \[]", line, 1)[0].strip()
            if package:
                req_map[package].add(req_file.name)
    return req_map


def iter_project_files() -> Iterable[Path]:
    for path in PROJECT_ROOT.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def analyze_usage(packages: Set[str]) -> Dict[str, Dict[str, object]]:
    usage = {pkg: {"imports": set()} for pkg in packages}
    for file_path in iter_project_files():
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            match = IMPORT_PATTERN.match(line)
            if not match:
                continue
            root_name = match.group(1).split(".")[0]
            if root_name in usage:
                usage[root_name]["imports"].add(str(file_path.relative_to(PROJECT_ROOT)))
    # convert sets to sorted lists
    for item in usage.values():
        item["imports"] = sorted(item["imports"])
    return usage


def analyze_logging() -> List[Dict[str, object]]:
    findings: List[Dict[str, object]] = []
    for file_path in iter_project_files():
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if "basicConfig" in line and "level=" in line:
                findings.append(
                    {
                        "file": str(file_path.relative_to(PROJECT_ROOT)),
                        "line": idx,
                        "statement": line.strip(),
                    }
                )
            match = LOG_LEVEL_PATTERN.search(line)
            if match:
                findings.append(
                    {
                        "file": str(file_path.relative_to(PROJECT_ROOT)),
                        "line": idx,
                        "level": match.group(1),
                        "statement": line.strip(),
                    }
                )
    return findings


def build_summary() -> Dict[str, object]:
    raw_req_map = list_requirements()
    usage_map = analyze_usage(set(raw_req_map.keys()))
    unused = sorted(pkg for pkg, info in usage_map.items() if not info["imports"])
    duplicates = [
        {"package": pkg, "files": sorted(files)}
        for pkg, files in raw_req_map.items()
        if len(files) > 1
    ]
    logging_findings = analyze_logging()

    timestamp = datetime.now(timezone.utc).isoformat()
    summary: Dict[str, object] = {
        "timestamp": timestamp,
        "requirements": {pkg: sorted(files) for pkg, files in raw_req_map.items()},
        "usage": usage_map,
        "unused_packages": unused,
        "duplicate_packages": duplicates,
        "logging_findings": logging_findings,
    }
    return summary


def main() -> None:
    args = parse_args()
    summary = build_summary()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = args.output_dir / f"dependency_log_audit_{stamp}.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Audit written to {output_path}")
    if summary["unused_packages"]:
        print("Potentially unused packages:", ", ".join(summary["unused_packages"]))
    if summary["logging_findings"]:
        print(
            f"Found {len(summary['logging_findings'])} logging statements to review "
            "(see JSON report)."
        )


if __name__ == "__main__":
    sys.exit(main())
