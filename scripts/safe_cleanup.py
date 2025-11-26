"""Safely remove legacy directories and helper files after dependency analysis."""

from __future__ import annotations

import argparse
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_introspection import (DEFAULT_EXCLUDED_DIRS, build_python_graph,
                                get_repo_root, iter_repo_files,
                                normalized_repo_path, run_git_grep, timestamp,
                                write_json)

DIR_TARGETS = {
    "examples",
    "old",
    "legacy",
    "draft",
    "notes",
    "ideas",
    "design_old",
    "backup_docs",
    "first_demo",
    "sample_game",
}
DIR_PREFIXES = ("prototype_",)
FILE_SUFFIXES = ("_old.py", "_backup.py")


def collect_directories(root: Path) -> list[Path]:
    """Locate directories that match cleanup rules."""

    excluded = {name.lower() for name in DEFAULT_EXCLUDED_DIRS}
    matches: list[Path] = []
    for dirpath, dirnames, _ in os.walk(root):
        path = Path(dirpath)
        if path == root:
            pass
        if any(
            part.lower() in excluded for part in path.relative_to(root).parts if part
        ):
            continue
        dirnames[:] = [d for d in dirnames if d.lower() not in excluded]
        if path == root:
            continue
        name = path.name.lower()
        if name in DIR_TARGETS or any(
            name.startswith(prefix) for prefix in DIR_PREFIXES
        ):
            matches.append(path)
    return matches


def collect_files(root: Path) -> list[Path]:
    """Locate file-level cleanup targets."""

    matches: list[Path] = []
    for path in iter_repo_files(root):
        if path.suffix == ".py" and path.name.startswith("test_"):
            if is_empty_test_file(path):
                matches.append(path)
                continue
        if any(path.name.endswith(suffix) for suffix in FILE_SUFFIXES):
            matches.append(path)
    return matches


def is_empty_test_file(path: Path) -> bool:
    """Return True if the test file never asserts anything."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "assert" not in text


def modules_under(path: Path, graph) -> list[str]:
    """Return module names defined under the provided directory."""

    modules: list[str] = []
    for module_name, info in graph.modules.items():
        try:
            info.path.relative_to(path)
        except ValueError:
            continue
        modules.append(module_name)
    return modules


def decide_action(
    path: Path,
    *,
    root: Path,
    graph,
    module_lookup: dict[str, str],
    module_tests: dict[str, list[str]],
    dry_run: bool,
) -> dict[str, Any]:
    rel_path = normalized_repo_path(path, root)
    modules: list[str] = []
    if path.is_file() and path.suffix == ".py":
        module_name = module_lookup.get(rel_path)
        if module_name:
            modules.append(module_name)
    elif path.is_dir():
        modules.extend(modules_under(path, graph))

    importers = sum(len(graph.reverse_imports.get(module, [])) for module in modules)
    test_refs = sum(len(module_tests.get(module, [])) for module in modules)
    git_hits = run_git_grep(rel_path, root, exclude_paths=[rel_path])

    flags: list[str] = []
    if git_hits:
        flags.append("reference_detected")
    if importers:
        flags.append("imported_module")
    if test_refs:
        flags.append("referenced_by_tests")

    action = "deleted"
    reason = "unused"
    if flags:
        action = "review_needed"
        reason = "references_detected"
    if action == "deleted" and not dry_run:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink(missing_ok=True)
    elif action == "deleted" and dry_run:
        action = "would_delete"
        reason = "dry_run"

    return {
        "path": rel_path,
        "type": "dir" if path.is_dir() else "file",
        "modules": modules,
        "action": action,
        "reason": reason,
        "ref_counts": {
            "git_grep": len(git_hits),
            "importers": importers,
            "test_refs": test_refs,
        },
        "flags": flags,
    }


def build_report(root: Path, *, dry_run: bool) -> dict[str, Any]:
    graph = build_python_graph(root)
    module_lookup = {info.rel_path: name for name, info in graph.modules.items()}
    module_tests: dict[str, list[str]] = defaultdict(list)
    for test_path, modules in graph.tests_to_modules.items():
        for module in modules:
            module_tests[module].append(test_path)

    actions: list[dict[str, Any]] = []
    processed: set[str] = set()

    for directory in collect_directories(root):
        if not directory.exists():
            continue
        rel_path = normalized_repo_path(directory, root)
        if rel_path in processed:
            continue
        actions.append(
            decide_action(
                directory,
                root=root,
                graph=graph,
                module_lookup=module_lookup,
                module_tests=module_tests,
                dry_run=dry_run,
            )
        )
        processed.add(rel_path)

    for file_path in collect_files(root):
        if not file_path.exists():
            continue
        rel_path = normalized_repo_path(file_path, root)
        if rel_path in processed:
            continue
        actions.append(
            decide_action(
                file_path,
                root=root,
                graph=graph,
                module_lookup=module_lookup,
                module_tests=module_tests,
                dry_run=dry_run,
            )
        )
        processed.add(rel_path)

    deleted = sum(1 for action in actions if action["action"] == "deleted")
    pending = sum(1 for action in actions if action["action"] == "review_needed")

    return {
        "generated_at": timestamp(),
        "root": str(root),
        "dry_run": dry_run,
        "deleted": deleted,
        "review_needed": pending,
        "actions": actions,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely delete unused legacy assets.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report planned deletions without touching the filesystem.",
    )
    parser.add_argument(
        "--output",
        default="logs/safe_cleanup_actions.json",
        help="Output JSON path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = get_repo_root()
    report = build_report(root, dry_run=args.dry_run)
    write_json(report, root / args.output)
    print(f"[safe_cleanup] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
