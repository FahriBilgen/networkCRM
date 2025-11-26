"""Shared helpers for repository analysis and cleanup automation."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

DEFAULT_EXCLUDED_DIRS: tuple[str, ...] = (
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    ".idea",
    ".vscode",
    ".ruff_cache",
)


def get_repo_root() -> Path:
    """Return the repository root inferred from this module location."""

    return Path(__file__).resolve().parents[1]


def iter_repo_files(
    root: Path,
    *,
    excluded_dirs: Sequence[str] = DEFAULT_EXCLUDED_DIRS,
) -> Iterator[Path]:
    """Yield every file inside the repository, skipping generated caches."""

    exclude = {name.lower() for name in excluded_dirs}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_parts = Path(dirpath).relative_to(root).parts
        if any(part.lower() in exclude for part in rel_parts):
            continue
        dirnames[:] = [name for name in dirnames if name.lower() not in exclude]
        for filename in filenames:
            yield Path(dirpath, filename)


def tail_lines(path: Path, limit: int = 50) -> list[str]:
    """Return the trailing N lines from a text file."""

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []
    lines = text.splitlines()
    return lines[-limit:]


def normalized_repo_path(path: Path, root: Path | None = None) -> str:
    """Return a POSIX-like path relative to the repository root."""

    root = root or get_repo_root()
    return path.resolve().relative_to(root).as_posix()


def module_name_from_path(path: Path, root: Path) -> str:
    """Convert a Python file path into its dotted module path."""

    relative = path.resolve().relative_to(root)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].rsplit(".", 1)[0]
    candidate = ".".join(parts).strip(".")
    if not candidate:
        candidate = relative.stem
    return candidate


def resolve_relative_module(
    current_module: str, level: int, target: str | None
) -> str | None:
    """Resolve a relative import to its absolute module path."""

    if level == 0:
        return target
    if not current_module:
        return target
    relative = "." * level + (target or "")
    try:
        return importlib.util.resolve_name(relative, current_module)
    except (ImportError, ValueError):
        return target


@dataclass(slots=True)
class ImportRecord:
    lineno: int
    module: str | None
    names: tuple[str, ...]
    level: int
    resolved: str | None


@dataclass(slots=True)
class ModuleInfo:
    module: str
    path: Path
    rel_path: str
    imports: list[str] = field(default_factory=list)
    import_records: list[ImportRecord] = field(default_factory=list)
    parse_error: str | None = None


@dataclass(slots=True)
class PythonGraph:
    modules: dict[str, ModuleInfo]
    import_matrix: dict[str, set[str]]
    reverse_imports: dict[str, set[str]]
    tests_to_modules: dict[str, set[str]]

    def unused_modules(self) -> list[str]:
        """Return modules that are never imported by any other file."""

        unused: list[str] = []
        for module_name, info in self.modules.items():
            if info.path.name == "__init__.py":
                continue
            normalized = info.rel_path.replace("\\", "/")
            if "/tests/" in normalized:
                continue
            if not self.reverse_imports.get(module_name):
                unused.append(module_name)
        return sorted(unused)


def build_python_graph(root: Path) -> PythonGraph:
    """Parse all Python files and construct the import graph."""

    modules: dict[str, ModuleInfo] = {}
    import_matrix: dict[str, set[str]] = {}
    tests_to_modules: dict[str, set[str]] = {}

    candidate_tests: list[ModuleInfo] = []
    for path in iter_repo_files(root):
        if path.suffix != ".py":
            continue
        rel_path = normalized_repo_path(path, root)
        module_name = module_name_from_path(path, root)
        info = ModuleInfo(module=module_name, path=path, rel_path=rel_path)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, UnicodeDecodeError, OSError) as exc:
            info.parse_error = f"{type(exc).__name__}: {exc}"
            modules[module_name] = info
            continue
        resolved_imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    resolved = name
                    record = ImportRecord(
                        lineno=node.lineno,
                        module=name,
                        names=(alias.asname or alias.name,),
                        level=0,
                        resolved=resolved,
                    )
                    info.import_records.append(record)
                    if resolved:
                        resolved_imports.add(resolved)
            elif isinstance(node, ast.ImportFrom):
                resolved = resolve_relative_module(module_name, node.level, node.module)
                alias_names = tuple(alias.name for alias in node.names)
                record = ImportRecord(
                    lineno=node.lineno,
                    module=node.module,
                    names=alias_names,
                    level=node.level,
                    resolved=resolved,
                )
                info.import_records.append(record)
                if resolved:
                    resolved_imports.add(resolved)
                    for alias in node.names:
                        if alias.name == "*":
                            continue
                        resolved_name = f"{resolved}.{alias.name}".strip(".")
                        if resolved_name:
                            resolved_imports.add(resolved_name)
        info.imports = sorted(resolved_imports)
        modules[module_name] = info
        if "tests/" in rel_path or Path(rel_path).name.startswith("test_"):
            candidate_tests.append(info)

    for module_name, info in modules.items():
        import_matrix[module_name] = set(info.imports)

    reverse_imports: dict[str, set[str]] = {name: set() for name in modules}
    for importer, targets in import_matrix.items():
        for target in targets:
            if target in reverse_imports:
                reverse_imports[target].add(importer)

    for info in candidate_tests:
        matched = {imp for imp in info.imports if imp in modules}
        if matched:
            tests_to_modules[info.rel_path] = matched

    return PythonGraph(
        modules=modules,
        import_matrix=import_matrix,
        reverse_imports=reverse_imports,
        tests_to_modules=tests_to_modules,
    )


def run_git_grep(
    pattern: str, root: Path, *, exclude_paths: Sequence[str] | None = None
) -> list[str]:
    """Run git grep for the provided pattern and return the matched lines."""

    if not pattern:
        return []
    cmd = ["git", "-C", str(root), "grep", "-n", "-F", pattern]
    excludes = [path for path in (exclude_paths or []) if path]
    if excludes:
        cmd.append("--")
        cmd.extend(f":(exclude){path}" for path in excludes)
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []
    if result.returncode not in (0, 1):
        return []
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return lines


def write_json(payload: dict, output_path: Path) -> None:
    """Persist a JSON payload with stable formatting."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def timestamp() -> str:
    """Return an ISO timestamp in UTC."""

    return datetime.now(timezone.utc).isoformat()
