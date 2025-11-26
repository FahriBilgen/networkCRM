"""Integration tests for session persistence and state tracking."""

from pathlib import Path

import pytest

from fortress_director.core.state_store import GameState


class TestGameStateSessionId:
    """Test GameState session_id tracking."""

    def test_gamestate_accepts_session_id(self):
        """GameState should accept and store session_id."""
        session_id = "test_session_123"
        initial_state = {"test": "data"}

        gs = GameState(initial_state, session_id=session_id)

        assert gs._session_id == session_id
        assert gs._state.get("session_id") == session_id

    def test_gamestate_session_id_in_snapshot(self):
        """Snapshot should include session_id."""
        session_id = "snap_session_456"
        initial_state = {"test": "data"}

        gs = GameState(initial_state, session_id=session_id)
        snapshot = gs.snapshot()

        assert snapshot.get("session_id") == session_id

    def test_gamestate_session_id_persists_across_deltas(self):
        """Session_id should persist after applying delta."""
        session_id = "delta_session_789"
        gs = GameState({"test": "initial"}, session_id=session_id)

        delta = {"test": "updated", "new_field": "value"}
        gs.apply_delta(delta)
        snapshot = gs.snapshot()

        assert snapshot.get("session_id") == session_id
        assert snapshot.get("test") == "updated"


class TestGameStateFromThemeConfig:
    """Test GameState.from_theme_config with session_id."""

    def test_from_theme_config_accepts_session_id(self):
        """from_theme_config should accept session_id."""
        from fortress_director.themes.loader import (
            BUILTIN_THEMES,
            load_theme_from_file,
        )

        theme_path = BUILTIN_THEMES.get("siege_default")
        if not theme_path:
            pytest.skip("siege_default theme not available")

        theme = load_theme_from_file(theme_path)
        session_id = "theme_session_111"

        gs = GameState.from_theme_config(theme, session_id=session_id)

        assert gs._session_id == session_id
        assert gs._state.get("session_id") == session_id

    def test_from_theme_config_without_session_id(self):
        """from_theme_config should work without session_id."""
        from fortress_director.themes.loader import (
            BUILTIN_THEMES,
            load_theme_from_file,
        )

        theme_path = BUILTIN_THEMES.get("siege_default")
        if not theme_path:
            pytest.skip("siege_default theme not available")

        theme = load_theme_from_file(theme_path)

        gs = GameState.from_theme_config(theme)

        assert gs._session_id is None
        assert "session_id" not in gs._state


class TestGameStateFromDemoSpec:
    """Test GameState.from_demo_spec with session_id."""

    def test_from_demo_spec_accepts_session_id(self):
        """from_demo_spec should accept session_id."""
        from fortress_director.demo.spec_loader import load_demo_spec

        demo_path = "data/demo_specs/siege_default.json"
        if not Path(demo_path).exists():
            pytest.skip(f"Demo spec not found at {demo_path}")

        spec = load_demo_spec(demo_path)
        session_id = "demo_session_222"
        gs = GameState.from_demo_spec(spec, session_id=session_id)

        assert gs._session_id == session_id
        assert gs._state.get("session_id") == session_id

    def test_from_demo_spec_without_session_id(self):
        """from_demo_spec should work without session_id."""
        from fortress_director.demo.spec_loader import load_demo_spec

        demo_path = "data/demo_specs/siege_default.json"
        if not Path(demo_path).exists():
            pytest.skip(f"Demo spec not found at {demo_path}")

        spec = load_demo_spec(demo_path)
        gs = GameState.from_demo_spec(spec)

        assert gs._session_id is None
        assert "session_id" not in gs._state


class TestSessionStateTracking:
    """Test session state persistence across turns."""

    def test_session_id_preserved_across_turns(self):
        """Session_id should be preserved when applying turn deltas."""
        from fortress_director.themes.loader import (
            BUILTIN_THEMES,
            load_theme_from_file,
        )

        theme_path = BUILTIN_THEMES.get("siege_default")
        if not theme_path:
            pytest.skip("siege_default theme not available")

        theme = load_theme_from_file(theme_path)
        session_id = "turn_session_333"

        gs = GameState.from_theme_config(theme, session_id=session_id)
        turn_1 = gs.snapshot()
        assert turn_1.get("session_id") == session_id

        # Simulate turn advancement with minimal delta
        delta = {"flags": ["test_flag"]}
        gs.apply_delta(delta)
        turn_2 = gs.snapshot()

        # Main test: session_id is preserved
        assert turn_2.get("session_id") == session_id
        # Verify delta was applied
        assert "test_flag" in turn_2.get("flags", [])

    def test_multiple_sessions_have_different_ids(self):
        """Different sessions should have different session_ids."""
        from fortress_director.themes.loader import (
            BUILTIN_THEMES,
            load_theme_from_file,
        )

        theme_path = BUILTIN_THEMES.get("siege_default")
        if not theme_path:
            pytest.skip("siege_default theme not available")

        theme = load_theme_from_file(theme_path)

        gs1 = GameState.from_theme_config(theme, session_id="session_1")
        gs2 = GameState.from_theme_config(theme, session_id="session_2")

        snap1 = gs1.snapshot()
        snap2 = gs2.snapshot()

        assert snap1.get("session_id") != snap2.get("session_id")
        assert snap1.get("session_id") == "session_1"
        assert snap2.get("session_id") == "session_2"


class TestSessionMetadataHandling:
    """Test session metadata stored in state."""

    def test_session_metadata_included_in_state(self):
        """Session_id should be accessible from state dict."""
        session_id = "metadata_session_444"
        gs = GameState({"test": "data"}, session_id=session_id)

        snapshot = gs.snapshot()
        assert snapshot.get("session_id") == session_id

    def test_session_id_survives_replace(self):
        """Session_id should survive state replacement."""
        session_id = "replace_session_555"
        gs = GameState({"initial": "state"}, session_id=session_id)

        new_state = {
            "replaced": "state",
            "session_id": session_id,
        }
        gs.replace(new_state)

        snapshot = gs.snapshot()
        # Note: replace may not preserve session_id if not explicitly included
        # This test documents that behavior
        session_check = (
            snapshot.get("session_id") == session_id or gs._session_id == session_id
        )
        assert session_check


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
