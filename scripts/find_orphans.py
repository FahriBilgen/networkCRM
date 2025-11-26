"""Identify potentially orphaned python modules."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_introspection import (build_python_graph, get_repo_root,
                                run_git_grep, timestamp, write_json)

KEYWORDS = ("TODO REMOVE", "LEGACY", "OLD", "EXAMPLE")
EXCLUDED_PREFIXES = ("scripts/",)
EXCLUDED_FILES = {"settings.py"}


def contains_removal_keyword(path: Path) -> bool:
    """Return True if the file contains one of the removal keywords."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    upper_text = text.upper()
    return any(keyword in upper_text for keyword in KEYWORDS)


def build_report(root: Path) -> dict[str, Any]:
    graph = build_python_graph(root)
    module_to_tests: dict[str, list[str]] = defaultdict(list)
    for test_path, modules in graph.tests_to_modules.items():
        for module in modules:
            module_to_tests[module].append(test_path)

    orphans: list[dict[str, Any]] = []
    for module_name, info in graph.modules.items():
        if info.path.name == "__init__.py":
            continue
        normalized = info.rel_path.replace("\\", "/")
        if "/tests/" in normalized:
            continue
        if any(normalized.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        if info.path.name in EXCLUDED_FILES:
            continue
        importers = sorted(graph.reverse_imports.get(module_name, []))
        if importers:
            continue
        tests = sorted(module_to_tests.get(module_name, []))
        flags: list[str] = ["orphan"]
        if not tests:
            flags.append("weak_candidate")
        if contains_removal_keyword(info.path):
            flags.append("remove_candidate")
        git_hits = run_git_grep(info.rel_path, root, exclude_paths=[info.rel_path])
        if git_hits:
            flags.append("review_reference_detected")
        orphans.append(
            {
                "module": module_name,
                "path": info.rel_path,
                "tests": tests,
                "flags": flags,
                "git_references": git_hits[:20],
            }
        )

    return {
        "generated_at": timestamp(),
        "root": str(root),
        "total_orphans": len(orphans),
        "orphans": sorted(orphans, key=lambda item: item["path"]),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find orphaned python modules.")
    parser.add_argument(
        "--output",
        default="logs/orphan_report.json",
        help="Output JSON file path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = get_repo_root()
    report = build_report(root)
    write_json(report, root / args.output)
    print(f"[find_orphans] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
