"""Unit tests for JWT token handling."""

import pytest
from datetime import timedelta
from fortress_director.auth.jwt_handler import (
    create_access_token,
    verify_token,
    decode_token,
)


class TestTokenCreation:
    """Test JWT token creation."""

    def test_create_access_token(self):
        """Should create a valid token."""
        session_id = "test_session_123"
        token = create_access_token(session_id)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2  # JWT format: header.payload.signature

    def test_token_contains_session_id(self):
        """Token should contain the session ID."""
        session_id = "session_abc"
        token = create_access_token(session_id)

        payload = decode_token(token)
        assert payload is not None
        assert payload.get("sub") == session_id

    def test_token_has_expiration(self):
        """Token should have an expiration claim."""
        session_id = "session_xyz"
        token = create_access_token(session_id)

        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload
        assert "iat" in payload

    def test_custom_expiration(self):
        """Should support custom expiration time."""
        session_id = "session_custom"
        custom_delta = timedelta(minutes=30)
        token = create_access_token(session_id, expires_delta=custom_delta)

        payload = decode_token(token)
        assert payload is not None
        assert "exp" in payload


class TestTokenVerification:
    """Test JWT token verification."""

    def test_verify_valid_token(self):
        """Should verify a valid token."""
        session_id = "test_session"
        token = create_access_token(session_id)

        verified_session_id = verify_token(token)
        assert verified_session_id == session_id

    def test_verify_invalid_token(self):
        """Should reject an invalid token."""
        invalid_token = "invalid.token.here"

        verified_session_id = verify_token(invalid_token)
        assert verified_session_id is None

    def test_verify_tampered_token(self):
        """Should reject a tampered token."""
        session_id = "test_session"
        token = create_access_token(session_id)

        # Tamper with token
        tampered = token[:-10] + "0123456789"

        verified_session_id = verify_token(tampered)
        assert verified_session_id is None

    def test_verify_empty_token(self):
        """Should reject empty token."""
        verified_session_id = verify_token("")
        assert verified_session_id is None


class TestTokenDecoding:
    """Test JWT token decoding."""

    def test_decode_valid_token(self):
        """Should decode a valid token."""
        session_id = "session_decode"
        token = create_access_token(session_id)

        payload = decode_token(token)
        assert payload is not None
        assert isinstance(payload, dict)
        assert payload.get("sub") == session_id

    def test_decode_invalid_token(self):
        """Should return None for invalid token."""
        invalid_token = "not.a.token"

        payload = decode_token(invalid_token)
        assert payload is None

    def test_decode_payload_structure(self):
        """Decoded payload should have required fields."""
        session_id = "payload_test"
        token = create_access_token(session_id)

        payload = decode_token(token)
        assert payload is not None
        assert "sub" in payload
        assert "exp" in payload
        assert "iat" in payload


class TestTokenMultipleSessions:
    """Test token isolation between sessions."""

    def test_different_tokens_for_different_sessions(self):
        """Each session should get a unique token."""
        token1 = create_access_token("session_1")
        token2 = create_access_token("session_2")

        assert token1 != token2

    def test_tokens_verify_independently(self):
        """Each token should verify to its own session."""
        token1 = create_access_token("session_1")
        token2 = create_access_token("session_2")

        assert verify_token(token1) == "session_1"
        assert verify_token(token2) == "session_2"
