from fortress_director.core.function_registry import SafeFunctionRegistry


def test_registry_has_many_functions():
    registry = SafeFunctionRegistry()
    all_meta = list(registry.list_metadata())
    # Expect at least 60 safe functions seeded in the registry
    assert len(all_meta) >= 60, "registry contains fewer than 60 functions"
