"""Diff helpers for Fortress Director world state snapshots."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Sequence, Set

DiffEntry = Dict[str, Any]
DEFAULT_IGNORED_KEYS: Set[str] = {
    "last_updated",
    "last_updated_turn",
    "last_repaired_turn",
    "last_reinforced_turn",
    "_glitch_buffer",
}


def compute_state_diff(
    previous: Dict[str, Any],
    current: Dict[str, Any],
    *,
    ignore_keys: Iterable[str] | None = None,
) -> List[DiffEntry]:
    """Return a normalized diff for two state dictionaries.

    Each diff entry is a dictionary with the fields:
    - ``path``: dotted path that identifies the mutated field.
    - ``kind``: one of ``added``, ``removed`` or ``changed``.
    - ``previous`` / ``current``: values before and after the change.
    """

    ignored = set(DEFAULT_IGNORED_KEYS)
    if ignore_keys:
        ignored.update(ignore_keys)
    diff: List[DiffEntry] = []

    def _walk(prev: Any, curr: Any, path: Sequence[str]) -> None:
        if prev is curr:
            return
        if _values_equal(prev, curr):
            return
        if isinstance(prev, dict) and isinstance(curr, dict):
            keys = set(prev.keys()) | set(curr.keys())
            for key in sorted(keys):
                if key in ignored:
                    continue
                sub_path = path + [str(key)]
                if key not in prev:
                    diff.append(
                        {
                            "path": _format_path(sub_path),
                            "kind": "added",
                            "current": curr[key],
                        }
                    )
                    continue
                if key not in curr:
                    diff.append(
                        {
                            "path": _format_path(sub_path),
                            "kind": "removed",
                            "previous": prev[key],
                        }
                    )
                    continue
                _walk(prev[key], curr[key], sub_path)
            return
        if isinstance(prev, list) and isinstance(curr, list):
            if prev != curr:
                diff.append(
                    {
                        "path": _format_path(path),
                        "kind": "changed",
                        "previous": prev,
                        "current": curr,
                    }
                )
            return
        diff.append(
            {
                "path": _format_path(path),
                "kind": "changed",
                "previous": prev,
                "current": curr,
            }
        )

    _walk(previous, current, [])
    return diff


def _values_equal(left: Any, right: Any) -> bool:
    try:
        return left == right
    except Exception:  # pragma: no cover - defensive
        return False


def _format_path(segments: Sequence[str]) -> str:
    if not segments:
        return "<root>"
    return ".".join(segments)


def apply_state_diff(
    state: Dict[str, Any],
    diff: Iterable[DiffEntry],
) -> Dict[str, Any]:
    """Apply a diff (as produced by ``compute_state_diff``) onto *state*."""

    for entry in diff or []:
        path = entry.get("path") or "<root>"
        kind = entry.get("kind", "changed")
        if path == "<root>":
            if kind == "removed":
                state.clear()
            else:
                state.clear()
                current = entry.get("current")
                if isinstance(current, dict):
                    state.update(current)
                else:
                    raise ValueError("Root diff requires a dict payload")
            continue

        segments = path.split(".")
        parent = state
        for segment in segments[:-1]:
            node = parent.get(segment)
            if not isinstance(node, dict):
                node = {}
                parent[segment] = node
            parent = node
        leaf = segments[-1]

        if kind == "removed":
            parent.pop(leaf, None)
            continue

        parent[leaf] = entry.get("current")

    return state
