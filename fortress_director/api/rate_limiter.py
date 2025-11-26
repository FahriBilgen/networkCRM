"""Rate limiting implementation using slowapi."""

from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create limiter instance with session-based key function
_limiter: Optional[Limiter] = None


def get_limiter() -> Limiter:
    """Get or create rate limiter instance."""
    global _limiter
    if _limiter is None:
        _limiter = Limiter(key_func=_get_rate_limit_key)
    return _limiter


def _get_rate_limit_key(request) -> str:
    """Extract rate limit key from request.

    Priority:
    1. Session ID from query parameter or body
    2. JWT token if present
    3. Remote address (fallback)
    """
    # Try to get session_id from query
    session_id = request.query_params.get("session_id")
    if session_id:
        return f"session:{session_id}"

    # Try to extract from JWT bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Use token as key (it's already unique per session)
        return f"token:{token}"

    # Fallback to remote address
    return f"ip:{get_remote_address(request)}"


# Predefined rate limit strings
LIMIT_TURNS = "30/minute"  # 30 turns per minute per session
LIMIT_LOGIN = "10/minute"  # 10 login attempts per minute
LIMIT_RESET = "5/minute"  # 5 reset attempts per minute
LIMIT_GENERIC = "60/minute"  # Generic 60 per minute
