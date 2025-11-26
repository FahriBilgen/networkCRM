"""Generate an exhaustive repository inventory and import analysis report."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from repo_introspection import (build_python_graph, get_repo_root,
                                iter_repo_files, normalized_repo_path,
                                tail_lines, timestamp, write_json)


def build_report(root: Path) -> dict[str, Any]:
    """Collect file metadata and python import analysis for the repository."""

    files: list[dict[str, Any]] = []
    for path in iter_repo_files(root):
        try:
            stat = path.stat()
        except OSError:
            continue
        rel_path = normalized_repo_path(path, root)
        files.append(
            {
                "path": rel_path,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "last_50_lines": tail_lines(path, limit=50),
            }
        )

    graph = build_python_graph(root)
    module_index = {name: info.rel_path for name, info in graph.modules.items()}
    imports_by_file: dict[str, list[str]] = {}
    for info in graph.modules.values():
        imports_by_file[info.rel_path] = sorted(info.imports)
    reverse_imports_readable: dict[str, list[str]] = {}
    for module_name, importers in graph.reverse_imports.items():
        if not importers:
            continue
        reverse_imports_readable[module_name] = sorted(importers)

    tests_reference_map: dict[str, list[str]] = {
        rel_path: sorted(modules)
        for rel_path, modules in graph.tests_to_modules.items()
    }

    unused_modules = graph.unused_modules()
    unused_paths = [
        graph.modules[name].rel_path for name in unused_modules if name in graph.modules
    ]

    return {
        "generated_at": timestamp(),
        "root": str(root),
        "file_inventory": {
            "total_files": len(files),
            "files": files,
        },
        "python_analysis": {
            "module_index": module_index,
            "imports_by_file": imports_by_file,
            "reverse_imports": reverse_imports_readable,
            "unused_python_modules": unused_paths,
            "tests_reference_map": tests_reference_map,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repository audit tool")
    parser.add_argument(
        "--output",
        default="logs/repo_audit_report.json",
        help="Destination JSON report path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = get_repo_root()
    report = build_report(root)
    output_path = root / args.output
    write_json(report, output_path)
    print(f"[repo_audit] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
