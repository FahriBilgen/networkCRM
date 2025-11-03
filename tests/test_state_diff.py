from __future__ import annotations

from fortress_director.utils.state_diff import compute_state_diff


def test_state_diff_same_state_returns_empty() -> None:
    assert compute_state_diff({"a": 1}, {"a": 1}) == []


def test_state_diff_detects_add_remove_change() -> None:
    previous = {"metrics": {"order": 10}, "flags": ["a"]}
    current = {"metrics": {"order": 12}, "flags": []}

    diff = compute_state_diff(previous, current)

    assert {
        "path": "metrics.order",
        "kind": "changed",
        "previous": 10,
        "current": 12,
    } in diff
    assert {
        "path": "flags",
        "kind": "changed",
        "previous": ["a"],
        "current": [],
    } in diff


def test_state_diff_ignores_keys() -> None:
    previous = {"last_updated": 1, "value": 2}
    current = {"last_updated": 2, "value": 3}

    diff = compute_state_diff(previous, current)

    assert diff == [
        {
            "path": "value",
            "kind": "changed",
            "previous": 2,
            "current": 3,
        }
    ]


def test_state_diff_custom_ignore_keys() -> None:
    previous = {"foo": 1, "bar": 2}
    current = {"foo": 2, "bar": 2}

    diff = compute_state_diff(previous, current, ignore_keys=["foo"])

    assert diff == []
