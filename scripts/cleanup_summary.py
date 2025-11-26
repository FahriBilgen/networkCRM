"""Aggregate cleanup artefacts into a single JSON report."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from repo_introspection import get_repo_root, timestamp, write_json


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def parse_git_status(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Return (deleted_files, renamed_entries) from git status."""

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--short"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return ([], [])
    deleted: list[str] = []
    renamed: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        payload = line[3:]
        if status.strip() == "D":
            deleted.append(payload.strip())
        elif status.strip().startswith("R"):
            if "->" in payload:
                old, new = (segment.strip() for segment in payload.split("->", 1))
                renamed.append({"from": old, "to": new})
    return deleted, renamed


def capture_import_changes(root: Path) -> list[str]:
    """Return summary lines for import changes detected in git diff."""

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--unified=0", "--", "*.py"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return []
    changes: list[str] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("+import ")
            or stripped.startswith("-import ")
            or stripped.startswith("+from ")
            or stripped.startswith("-from ")
        ):
            changes.append(stripped)
    return changes


def build_report(root: Path) -> dict[str, Any]:
    safe_cleanup = read_json(root / "logs" / "safe_cleanup_actions.json")
    orphan_report = read_json(root / "logs" / "orphan_report.json")
    audit_report = read_json(root / "logs" / "repo_audit_report.json")
    deadcode_report = read_json(root / "logs" / "deadcode_report.json")

    deleted_files, renamed_entries = parse_git_status(root)
    import_changes = capture_import_changes(root)

    if safe_cleanup:
        deleted_files.extend(
            action["path"]
            for action in safe_cleanup.get("actions", [])
            if action.get("action") == "deleted"
        )

    orphan_modules = orphan_report.get("orphans", []) if orphan_report else []
    deadcode = deadcode_report.get("analysis", {}) if deadcode_report else {}

    risks: list[str] = []
    if safe_cleanup:
        risks.extend(
            action["path"]
            for action in safe_cleanup.get("actions", [])
            if action.get("action") == "review_needed"
        )
    if orphan_modules:
        risks.extend(orphan["path"] for orphan in orphan_modules)

    summary = {
        "generated_at": timestamp(),
        "root": str(root),
        "deleted_files": sorted(set(deleted_files)),
        "moved_files": renamed_entries,
        "import_changes": import_changes[:200],
        "deadcode_summary": {
            "unused_functions": len(deadcode.get("unused_functions", [])),
            "unused_classes": len(deadcode.get("unused_classes", [])),
            "duplicate_functions": len(deadcode.get("duplicate_functions", [])),
        },
        "orphans": orphan_modules,
        "remaining_risks": sorted(set(risks)),
        "audit_reference": (
            audit_report.get("file_inventory", {}).get("total_files")
            if audit_report
            else None
        ),
    }
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a consolidated cleanup report."
    )
    parser.add_argument(
        "--output",
        default="logs/cleanup_report.json",
        help="Path for the summary JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = get_repo_root()
    report = build_report(root)
    write_json(report, root / args.output)
    print(f"[cleanup_summary] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
