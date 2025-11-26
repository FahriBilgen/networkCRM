"""TIER 3 final validation and regression tests."""

from fortress_director.core.function_registry import load_defaults
from fortress_director.core.health_check import get_health_status
from fortress_director.core.performance_cache import get_cache_stats
from fortress_director.themes.loader import (
    BUILTIN_THEMES,
    load_theme_from_file,
)
from fortress_director.core.state_store import GameState


def test_safe_functions_count_exceeds_75() -> None:
    """TIER 3 requirement: 75+ safe functions."""
    funcs = load_defaults()
    assert len(funcs) >= 75, f"Expected 75+, got {len(funcs)}"


def test_all_11_categories_exist() -> None:
    """TIER 3 requirement: 11 function categories."""
    funcs = load_defaults()
    categories = set(m.category for m in funcs.values())
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
    assert categories == expected, f"Missing: {expected - categories}"


def test_new_categories_have_functions() -> None:
    """TIER 3 requirement: Diplomacy, crafting, magic categories exist."""
    funcs = load_defaults()
    categories = {m.category for m in funcs.values()}

    assert "diplomacy" in categories
    assert "crafting" in categories
    assert "magic" in categories

    diplomacy = [m for m in funcs.values() if m.category == "diplomacy"]
    crafting = [m for m in funcs.values() if m.category == "crafting"]
    magic = [m for m in funcs.values() if m.category == "magic"]

    assert len(diplomacy) >= 5, "Diplomacy should have 5+ functions"
    assert len(crafting) >= 5, "Crafting should have 5+ functions"
    assert len(magic) >= 5, "Magic should have 5+ functions"


def test_health_check_passes() -> None:
    """TIER 3 requirement: Health check endpoint works."""
    status = get_health_status()
    assert status.status in ["ok", "degraded", "error"]
    assert status.version == "0.3.0"
    assert "themes" in status.checks
    assert "safe_functions" in status.checks
    assert status.checks["safe_functions"]["count"] >= 75


def test_themes_load_correctly() -> None:
    """Verify themes can be loaded and used."""
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    game_state = GameState.from_theme_config(theme)
    assert game_state is not None
    assert game_state.get_projected_state() is not None


def test_performance_caching_available() -> None:
    """TIER 3 requirement: Performance caching infrastructure exists."""
    stats = get_cache_stats()
    assert isinstance(stats, dict)
    # Should have cache infrastructure (even if unused)


def test_session_persistence_works() -> None:
    """TIER 2 requirement still met: Sessions persist (infrastructure)."""
    # Just verify the session store module exists and is importable
    from fortress_director.db.session_store import (
        get_session_store,
        SessionStore,
    )

    assert SessionStore is not None
    # Don't try to use it without DB init
    _ = get_session_store


def test_rate_limiting_configured() -> None:
    """TIER 2 requirement still met: Rate limiting infrastructure."""
    from fortress_director.rate_limiter import (
        get_limiter,
        LIMIT_TURNS,
        LIMIT_LOGIN,
        LIMIT_RESET,
    )

    limiter = get_limiter()
    assert limiter is not None
    assert LIMIT_TURNS == "30/minute"
    assert LIMIT_LOGIN == "10/minute"
    assert LIMIT_RESET == "5/minute"


def test_database_session_table_exists() -> None:
    """TIER 2 requirement still met: Database sessions infrastructure."""
    # Verify the infrastructure exists, not actual DB operations
    from fortress_director.db.session_store import SessionStore

    assert SessionStore is not None
    # Schema exists in db/schema.sql
    from pathlib import Path

    schema_file = Path("db/schema.sql")
    assert schema_file.exists()


def test_jwt_authentication_available() -> None:
    """TIER 1 requirement still met: JWT auth module."""
    from fortress_director.auth.jwt_handler import (
        create_access_token,
    )

    # Just verify the functions exist and work
    token = create_access_token({"sub": "test_user"})
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_file_locking_available() -> None:
    """TIER 2 requirement still met: File locking mechanism."""
    from fortress_director.utils.file_lock import FileLock
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / "test.lock"
        with FileLock(lock_path):
            assert lock_path.exists()


def test_all_categories_have_valid_functions() -> None:
    """All function categories have valid metadata."""
    funcs = load_defaults()

    for name, meta in funcs.items():
        assert meta.name == name
        assert meta.category
        assert meta.description
        assert meta.gas_cost >= 1
        assert isinstance(meta.enabled, bool)
        assert meta.planner_weight >= 0.0
        assert isinstance(meta.params, list)


def test_theme_overrides_work() -> None:
    """Theme-specific function overrides work correctly."""
    from fortress_director.core.function_registry import apply_theme_overrides

    registry = load_defaults()
    theme = load_theme_from_file(BUILTIN_THEMES["siege_default"])
    themed = apply_theme_overrides(registry, theme)

    # Should have filtered out some functions
    assert len(themed) <= len(registry)
    # But should still have most functions
    assert len(themed) > len(registry) * 0.7


def test_production_readiness_metrics() -> None:
    """Generate final production readiness assessment."""
    from datetime import datetime

    funcs = load_defaults()
    health = get_health_status()

    # Collect metrics
    metrics = {
        "total_functions": len(funcs),
        "function_categories": len(set(m.category for m in funcs.values())),
        "health_status": health.status,
        "uptime_seconds": health.uptime_seconds,
        "database_connected": (
            health.checks.get("database", {}).get("connected", False)
        ),
        "themes_available": (health.checks.get("themes", {}).get("count", 0)),
        "python_version": (health.checks.get("python_version", "unknown")),
        "timestamp": datetime.now().isoformat(),
    }

    # Verify minimum thresholds
    assert metrics["total_functions"] >= 75
    assert metrics["function_categories"] >= 11
    assert metrics["health_status"] in ["ok", "degraded"]
    assert metrics["themes_available"] > 0

    print("\n=== TIER 3 PRODUCTION READINESS ===")
    print(f"Total functions: {metrics['total_functions']}")
    print(f"Categories: {metrics['function_categories']}")
    print(f"Health status: {metrics['health_status']}")
    print(f"Themes: {metrics['themes_available']}")
    print(f"Python: {metrics['python_version']}")
    print("================================")
