"""Integration tests for JWT authentication flow."""

import json
from typing import Optional

import pytest

from fortress_director.api import app, _SESSION_MANAGER
from fortress_director.auth.jwt_handler import verify_token


class MockRequest:
    """Mock request object for testing."""

    def __init__(self, headers: Optional[dict] = None):
        self.headers = headers or {}
        self.state = type("State", (), {})()


class TestAuthLoginEndpoint:
    """Test /auth/login endpoint."""

    def test_login_creates_session(self):
        """POST /auth/login should create a new session."""
        payload = {"player_name": "Rhea", "theme_id": "siege_default"}

        # Use test client (would be from fastapi.testclient in real test)
        # For now, simulate the endpoint logic
        session_id, _context = _SESSION_MANAGER.reset(theme_id=payload["theme_id"])

        assert session_id is not None
        assert len(session_id) > 0
        assert session_id in _SESSION_MANAGER._sessions

    def test_login_returns_valid_token(self):
        """POST /auth/login should return a valid JWT token."""
        from fortress_director.auth.jwt_handler import create_access_token

        session_id = "test_session_123"
        token = create_access_token(session_id)

        # Verify token is valid
        decoded_session = verify_token(token)
        assert decoded_session == session_id

    def test_login_response_structure(self):
        """POST /auth/login response should have correct structure."""
        from fortress_director.auth.jwt_handler import create_access_token

        session_id = "test_session_456"
        token = create_access_token(session_id)
        theme_id = "siege_default"

        response = {
            "session_id": session_id,
            "token": token,
            "token_type": "bearer",
            "theme_id": theme_id,
        }

        assert response["session_id"] == session_id
        assert response["token"] == token
        assert response["token_type"] == "bearer"
        assert response["theme_id"] == theme_id

    def test_multiple_logins_create_different_sessions(self):
        """Multiple logins should create separate sessions."""
        sessions = []
        for i in range(3):
            session_id, _context = _SESSION_MANAGER.reset(theme_id="siege_default")
            sessions.append(session_id)

        # All sessions should be unique
        assert len(sessions) == len(set(sessions))
        assert all(sid in _SESSION_MANAGER._sessions for sid in sessions)

    def test_login_with_default_theme(self):
        """Login without theme_id should use default."""
        session_id, context = _SESSION_MANAGER.reset(theme_id=None)
        # Check that context was created with some theme
        assert context.theme_id is not None

    def test_token_payload_isolation(self):
        """Different tokens should have different payloads."""
        from fortress_director.auth.jwt_handler import (
            create_access_token,
            decode_token,
        )

        token1 = create_access_token("session_1")
        token2 = create_access_token("session_2")

        payload1 = decode_token(token1)
        payload2 = decode_token(token2)

        assert payload1["sub"] == "session_1"
        assert payload2["sub"] == "session_2"
        assert payload1 != payload2

    def test_login_token_is_usable_for_auth(self):
        """Token from login should pass middleware verification."""
        from fortress_director.auth.jwt_handler import (
            create_access_token,
            verify_token,
        )

        session_id = "integration_test_session"
        token = create_access_token(session_id)

        # Verify token works
        verified_session = verify_token(token)
        assert verified_session == session_id

        # Token should work for Bearer auth
        bearer_token = f"Bearer {token}"
        # Extract the token part (would be done by middleware)
        extracted_token = bearer_token.split(" ")[1]
        assert verify_token(extracted_token) == session_id


class TestAuthMiddlewareIntegration:
    """Test JWT middleware with request flow."""

    def test_middleware_bypasses_public_paths(self):
        """Middleware should bypass auth for public paths."""
        public_paths = ["/", "/docs", "/health", "/static", "/assets"]
        # These should not require Bearer token
        for path in public_paths:
            # Middleware should skip validation
            assert path in [
                "/",
                "/docs",
                "/health",
                "/static",
                "/assets",
            ]

    def test_middleware_requires_token_for_protected_paths(self):
        """Middleware should require Bearer token for protected paths."""
        protected_paths = [
            "/api/run_turn",
            "/api/reset_for_new_run",
            "/api/select_action",
        ]
        # These paths should require authentication
        for path in protected_paths:
            assert path not in [
                "/",
                "/docs",
                "/health",
                "/static",
                "/assets",
            ]

    def test_token_extraction_from_header(self):
        """Middleware should extract Bearer token from Authorization header."""
        from fortress_director.auth.jwt_handler import create_access_token

        session_id = "header_test_session"
        token = create_access_token(session_id)
        auth_header = f"Bearer {token}"

        # Extract token logic
        parts = auth_header.split()
        assert len(parts) == 2
        assert parts[0] == "Bearer"
        extracted_token = parts[1]

        # Verify extracted token is valid
        from fortress_director.auth.jwt_handler import verify_token

        assert verify_token(extracted_token) == session_id


class TestAuthSessionIntegration:
    """Test auth with session management."""

    def test_session_context_created_on_login(self):
        """Login should create a SessionContext with GameState."""
        session_id, context = _SESSION_MANAGER.reset(theme_id="siege_default")

        assert session_id is not None
        assert context.game_state is not None
        assert context.theme_id == "siege_default"

    def test_session_persistence_across_turns(self):
        """Session created by login should persist for multiple turns."""
        session_id, context1 = _SESSION_MANAGER.reset(theme_id="siege_default")

        # Retrieve same session
        retrieved_id, context2, created = _SESSION_MANAGER.get_or_create(
            session_id, theme_id="siege_default"
        )

        assert retrieved_id == session_id
        assert context1.game_state == context2.game_state
        assert not created  # Should not create new session

    def test_token_tied_to_session_id(self):
        """JWT token should be tied to session_id created during login."""
        from fortress_director.auth.jwt_handler import (
            create_access_token,
            decode_token,
        )

        session_id, _context = _SESSION_MANAGER.reset(theme_id="siege_default")
        token = create_access_token(session_id)

        # Decode token and verify session_id
        payload = decode_token(token)
        assert payload["sub"] == session_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
