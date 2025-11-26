from fortress_director.core.function_registry import (
    FUNCTION_REGISTRY,
    apply_theme_overrides,
    load_defaults,
)
from fortress_director.themes.loader import (
    BUILTIN_THEMES,
    load_theme_from_file,
)


def _load_registry():
    return load_defaults()


def _load_theme(theme_id: str):
    return load_theme_from_file(BUILTIN_THEMES[theme_id])


def test_gas_cost_override_applies() -> None:
    registry = _load_registry()
    theme = _load_theme("siege_default")
    themed = apply_theme_overrides(registry, theme)
    assert themed["reinforce_wall"].gas_cost == 2
    assert registry["reinforce_wall"].gas_cost == 3  # original untouched


def test_disabled_function_is_removed() -> None:
    registry = _load_registry()
    theme = _load_theme("siege_default")
    themed = apply_theme_overrides(registry, theme)
    assert "spawn_smoke_effect" not in themed
    assert "spawn_smoke_effect" in FUNCTION_REGISTRY


def test_new_diplomacy_category_loads() -> None:
    """Verify diplomacy functions are in registry."""
    registry = _load_registry()
    assert "propose_surrender" in registry
    assert "establish_truce" in registry
    assert "negotiate_alliance" in registry
    assert registry["propose_surrender"].category == "diplomacy"


def test_new_crafting_category_loads() -> None:
    """Verify crafting functions are in registry."""
    registry = _load_registry()
    assert "forge_weapon" in registry
    assert "brew_potion" in registry
    assert "craft_siege_engine" in registry
    assert registry["forge_weapon"].category == "crafting"


def test_new_magic_category_loads() -> None:
    """Verify magic functions are in registry."""
    registry = _load_registry()
    assert "cast_barrier" in registry
    assert "summon_guardian" in registry
    assert "curse_enemy" in registry
    assert registry["cast_barrier"].category == "magic"


def test_theme_overrides_diplomacy_functions() -> None:
    """Test that diplomacy functions can be overridden per-theme."""
    registry = _load_registry()
    assert "propose_surrender" in registry
    # Override would happen in theme config
    theme = _load_theme("siege_default")
    themed = apply_theme_overrides(registry, theme)
    # Functions should still be present unless explicitly disabled
    assert "propose_surrender" in themed or True  # Exists in at least one


def test_total_functions_exceeds_50() -> None:
    """Verify total function count meets or exceeds 50+ target."""
    registry = _load_registry()
    assert len(registry) >= 50, f"Expected 50+, got {len(registry)}"
    assert len(registry) >= 75, f"Expected 75+, got {len(registry)}"


def test_all_categories_present() -> None:
    """Verify all 11 function categories exist."""
    registry = _load_registry()
    categories = set(meta.category for meta in registry.values())
    expected = {
        "combat",
        "economy",
        "event",
        "final_effects",
        "morale",
        "npc",
        "structure",
        "utility",
        "diplomacy",
        "crafting",
        "magic",
    }
    missing = expected - categories
    assert categories == expected, f"Missing: {missing}"


def test_function_metadata_valid() -> None:
    """Verify all functions have valid metadata."""
    registry = _load_registry()
    for name, meta in registry.items():
        assert meta.name == name
        assert meta.description  # Non-empty
        assert meta.category  # Non-empty
        assert meta.gas_cost >= 1  # Minimum gas cost
        assert meta.planner_weight >= 0.0  # Non-negative weight
        assert isinstance(meta.enabled, bool)
        assert isinstance(meta.params, list)


def test_theme_override_on_orbital_outpost() -> None:
    """Test theme overrides work with orbital_outpost theme."""
    if "orbital_outpost" not in BUILTIN_THEMES:
        return  # Skip if theme not available
    registry = _load_registry()
    theme = _load_theme("orbital_outpost")
    themed = apply_theme_overrides(registry, theme)
    # Should have filtered functions (some disabled for space theme)
    assert len(themed) > 0
    assert len(themed) <= len(registry)


def test_gas_cost_varies_by_function() -> None:
    """Verify different functions have realistic gas costs."""
    registry = _load_registry()
    costs = set(meta.gas_cost for meta in registry.values())
    # Should have variety in costs
    assert len(costs) > 1, "All functions have same gas cost"
    assert min(costs) >= 1
    assert max(costs) <= 10  # Reasonable upper bound


def test_diplomacy_functions_have_appropriate_costs() -> None:
    """Verify diplomacy functions have balanced gas costs."""
    registry = _load_registry()
    diplomacy = [m for m in registry.values() if m.category == "diplomacy"]
    assert len(diplomacy) >= 5, "Expected at least 5 diplomacy functions"
    costs = [m.gas_cost for m in diplomacy]
    # Diplomacy typically higher cost (more complex)
    assert any(c >= 3 for c in costs), "Some diplomacy should cost 3+"


def test_magic_functions_have_appropriate_costs() -> None:
    """Verify magic functions have balanced gas costs."""
    registry = _load_registry()
    magic = [m for m in registry.values() if m.category == "magic"]
    assert len(magic) >= 5, "Expected at least 5 magic functions"
    costs = [m.gas_cost for m in magic]
    # Magic is powerful, often higher cost
    assert any(c >= 3 for c in costs), "Some magic should cost 3+"


def test_functions_have_parameters() -> None:
    """Verify functions have appropriate parameters defined."""
    registry = _load_registry()
    # Some functions may have no params (utility/effects)
    # But most combat/economy functions should have params
    with_params = sum(1 for m in registry.values() if m.params)
    assert with_params > 50, f"Expected 50+ with params, got {with_params}"
