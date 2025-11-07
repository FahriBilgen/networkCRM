#!/usr/bin/env python3
"""Run the default mini regression suite and archive the results."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run unit + integration regressions and store artefacts.",
    )
    parser.add_argument(
        "--tag",
        help="Optional suffix for the regression directory.",
    )
    parser.add_argument(
        "--skip-unit",
        action="store_true",
        help="Skip the unit/offline pytest invocation.",
    )
    parser.add_argument(
        "--skip-integration",
        action="store_true",
        help="Skip the integration pytest invocation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not execute commands; create the directory and planned metadata only.",
    )
    parser.add_argument(
        "--unit-cmd",
        default='pytest -m "not integration" --maxfail=1',
        help='Command used for the unit/offline suite (default: %(default)s).',
    )
    parser.add_argument(
        "--integration-cmd",
        default="pytest -m integration --maxfail=1",
        help='Command used for the integration suite (default: %(default)s).',
    )
    return parser.parse_args()


def _shell_command(cmd: str) -> List[str]:
    return shlex.split(cmd)


def run_command(command: str, log_path: Path, dry_run: bool = False) -> Dict[str, object]:
    result: Dict[str, object] = {
        "command": command,
    }
    if dry_run:
        log_path.write_text("DRY RUN - command not executed.\n", encoding="utf-8")
        result.update({"status": "skipped", "duration_s": 0.0, "return_code": None})
        return result

    start = time.time()
    proc = subprocess.Popen(
        _shell_command(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    with log_path.open("w", encoding="utf-8") as handle:
        if proc.stdout:
            for line in proc.stdout:
                handle.write(line)
    return_code = proc.wait()
    duration = time.time() - start
    result.update(
        {
            "status": "passed" if return_code == 0 else "failed",
            "duration_s": round(duration, 2),
            "return_code": return_code,
        }
    )
    return result


def main() -> None:
    args = parse_args()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    tag = args.tag or f"regression_{timestamp}"
    target_dir = Path("runs/regressions") / tag
    target_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, object] = {
        "timestamp": timestamp,
        "directory": str(target_dir.resolve()),
        "python": sys.version,
        "runs": [],
    }

    if not args.skip_unit:
        log_path = target_dir / "unit.log"
        summary["runs"].append(
            {"suite": "unit", **run_command(args.unit_cmd, log_path, args.dry_run)}
        )

    if not args.skip_integration:
        log_path = target_dir / "integration.log"
        summary["runs"].append(
            {
                "suite": "integration",
                **run_command(args.integration_cmd, log_path, args.dry_run),
            }
        )

    summary_path = target_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        f"# Regression Report ({timestamp})",
        f"- Directory: `{summary['directory']}`",
    ]
    for run in summary["runs"]:
        md_lines.append(
            f"- **{run['suite']}**: {run['status']} "
            f"(cmd: `{run['command']}` | duration {run['duration_s']}s)"
        )
    (target_dir / "summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"Regression artefacts written to {target_dir}")


if __name__ == "__main__":
    main()
