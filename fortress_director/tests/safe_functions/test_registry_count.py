from __future__ import annotations

from fortress_director.core.function_registry import load_defaults


def test_registry_contains_minimum_entries() -> None:
    registry = load_defaults()
    assert len(registry) >= 60
    for meta in registry.values():
        assert meta.category
        assert isinstance(meta.params, list)
