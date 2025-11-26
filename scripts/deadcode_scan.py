"""Static analysis helpers to surface dead code and duplicate logic."""

from __future__ import annotations

import argparse
import ast
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from repo_introspection import (get_repo_root, iter_repo_files,
                                normalized_repo_path, timestamp, write_json)

SPECIAL_KEYWORDS = (
    "function_executor",
    "state_projection",
    "fallback",
    "prompt_builder",
    "worldrenderer",
)


@dataclass(slots=True)
class FunctionDetail:
    name: str
    qualname: str
    module: str
    signature: str
    path: str
    lineno: int
    body_hash: str
    unreachable_lines: list[int]
    unused_locals: list[str]


@dataclass(slots=True)
class ClassDetail:
    name: str
    qualname: str
    module: str
    path: str
    lineno: int


class ModuleVisitor(ast.NodeVisitor):
    """Collect function/class metadata for a module."""

    def __init__(self, module: str, rel_path: str) -> None:
        self.module = module
        self.rel_path = rel_path
        self.scope: list[str] = []
        self.functions: list[FunctionDetail] = []
        self.classes: list[ClassDetail] = []
        self.call_names: set[str] = set()
        self.name_loads: set[str] = set()
        self.print_calls: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:  # noqa: ANN401
        self._register_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:  # noqa: ANN401
        self._register_function(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:  # noqa: ANN401
        qualname = ".".join(self.scope + [node.name]) if self.scope else node.name
        detail = ClassDetail(
            name=node.name,
            qualname=f"{self.module}.{qualname}",
            module=self.module,
            path=self.rel_path,
            lineno=node.lineno,
        )
        self.classes.append(detail)
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> Any:  # noqa: ANN401
        names = extract_call_names(node.func)
        self.call_names.update(names)
        if any(name == "print" for name in names):
            self.print_calls.append({"path": self.rel_path, "line": node.lineno})
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> Any:  # noqa: ANN401
        if isinstance(node.ctx, ast.Load):
            self.name_loads.add(node.id)
        self.generic_visit(node)

    def _register_function(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qualname = ".".join(self.scope + [node.name]) if self.scope else node.name
            signature = format_signature(node)
            body_hash = hashlib.sha256(ast.dump(node).encode("utf-8")).hexdigest()
            unreachable = find_unreachable_lines(node.body)
            unused_locals = find_unused_locals(node)
            detail = FunctionDetail(
                name=node.name,
                qualname=f"{self.module}.{qualname}",
                module=self.module,
                signature=signature,
                path=self.rel_path,
                lineno=node.lineno,
                body_hash=body_hash,
                unreachable_lines=unreachable,
                unused_locals=unused_locals,
            )
            self.functions.append(detail)


def extract_call_names(node: ast.AST) -> set[str]:
    """Return {name, dotted.name} references for a call target."""

    names: set[str] = set()
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, ast.Attribute):
        parts: list[str] = []
        cursor = node
        while isinstance(cursor, ast.Attribute):
            parts.append(cursor.attr)
            cursor = cursor.value
        if isinstance(cursor, ast.Name):
            parts.append(cursor.id)
        dotted = ".".join(reversed(parts))
        if dotted:
            names.add(dotted)
            names.add(parts[0])
    return names


def format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [arg.arg for arg in node.args.args]
    if node.args.vararg:
        args.append(f"*{node.args.vararg.arg}")
    if node.args.kwarg:
        args.append(f"**{node.args.kwarg.arg}")
    return f"{node.name}({', '.join(args)})"


def find_unreachable_lines(body: list[ast.stmt]) -> list[int]:
    unreachable: list[int] = []
    terminated = False
    for stmt in body:
        if terminated:
            unreachable.append(stmt.lineno)
            continue
        if isinstance(stmt, (ast.Return, ast.Raise)):
            terminated = True
    return unreachable


class UsageVisitor(ast.NodeVisitor):
    """Track assigned and used variables within a function scope."""

    def __init__(self) -> None:
        self.assigned: set[str] = set()
        self.used: set[str] = set()

    def visit_Name(self, node: ast.Name) -> Any:  # noqa: ANN401
        if isinstance(node.ctx, ast.Store):
            self.assigned.add(node.id)
        elif isinstance(node.ctx, ast.Load):
            self.used.add(node.id)
        self.generic_visit(node)


def find_unused_locals(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    visitor = UsageVisitor()
    for stmt in node.body:
        visitor.visit(stmt)
    params = {arg.arg for arg in node.args.args}
    if node.args.vararg:
        params.add(node.args.vararg.arg)
    if node.args.kwarg:
        params.add(node.args.kwarg.arg)
    unused = [
        name
        for name in visitor.assigned
        if name not in visitor.used and name not in params and not name.startswith("_")
    ]
    return sorted(unused)


def scan_repository(root: Path) -> dict[str, Any]:
    functions: list[FunctionDetail] = []
    classes: list[ClassDetail] = []
    call_names: set[str] = set()
    name_loads: set[str] = set()
    print_statements: list[dict[str, Any]] = []

    for path in iter_repo_files(root):
        if path.suffix != ".py":
            continue
        rel_path = normalized_repo_path(path, root)
        module = rel_path.replace("/", ".").rsplit(".", 1)[0]
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        visitor = ModuleVisitor(module=module, rel_path=rel_path)
        visitor.visit(tree)
        functions.extend(visitor.functions)
        classes.extend(visitor.classes)
        call_names.update(visitor.call_names)
        name_loads.update(visitor.name_loads)
        print_statements.extend(visitor.print_calls)

    unused_functions = [
        func
        for func in functions
        if func.name not in call_names and func.qualname not in call_names
    ]
    unused_classes = [
        cls
        for cls in classes
        if cls.name not in name_loads and cls.qualname not in call_names
    ]

    duplicates: list[dict[str, Any]] = []
    grouped: defaultdict[tuple[str, str], list[FunctionDetail]] = defaultdict(list)
    for func in functions:
        grouped[(func.name, func.signature)].append(func)
    for (name, signature), group in grouped.items():
        body_hashes = {func.body_hash for func in group}
        if len(group) > 1 and len(body_hashes) > 1:
            duplicates.append(
                {
                    "name": name,
                    "signature": signature,
                    "definitions": [
                        {"path": func.path, "line": func.lineno, "module": func.module}
                        for func in group
                    ],
                }
            )

    unreachable = [
        {"path": func.path, "line": line, "function": func.qualname}
        for func in functions
        for line in func.unreachable_lines
    ]
    unused_variables = [
        {"path": func.path, "function": func.qualname, "variables": func.unused_locals}
        for func in functions
        if func.unused_locals
    ]

    special_alerts: list[dict[str, Any]] = []
    for func in unused_functions:
        lowered = func.name.lower()
        for keyword in SPECIAL_KEYWORDS:
            if keyword in lowered:
                special_alerts.append(
                    {
                        "keyword": keyword,
                        "path": func.path,
                        "symbol": func.qualname,
                        "line": func.lineno,
                        "kind": "function",
                    }
                )
                break
    for cls in unused_classes:
        lowered = cls.name.lower()
        for keyword in SPECIAL_KEYWORDS:
            if keyword in lowered:
                special_alerts.append(
                    {
                        "keyword": keyword,
                        "path": cls.path,
                        "symbol": cls.qualname,
                        "line": cls.lineno,
                        "kind": "class",
                    }
                )
                break

    return {
        "unused_functions": [
            {"path": func.path, "line": func.lineno, "function": func.qualname}
            for func in unused_functions
        ],
        "unused_classes": [
            {"path": cls.path, "line": cls.lineno, "class": cls.qualname}
            for cls in unused_classes
        ],
        "duplicate_functions": duplicates,
        "unreachable_code": unreachable,
        "print_statements": print_statements,
        "unused_variables": unused_variables,
        "special_alerts": special_alerts,
    }


def build_report(root: Path) -> dict[str, Any]:
    scan = scan_repository(root)
    return {
        "generated_at": timestamp(),
        "root": str(root),
        "analysis": scan,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dead code and duplicate logic scanner."
    )
    parser.add_argument(
        "--output",
        default="logs/deadcode_report.json",
        help="Output JSON path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = get_repo_root()
    report = build_report(root)
    write_json(report, root / args.output)
    print(f"[deadcode_scan] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
