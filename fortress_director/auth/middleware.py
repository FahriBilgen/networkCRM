"""FastAPI middleware for JWT token verification."""

from typing import Callable
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fortress_director.auth.jwt_handler import verify_token
from starlette.middleware.base import BaseHTTPMiddleware


class JWTMiddleware(BaseHTTPMiddleware):
    """
    Middleware to verify JWT tokens on protected endpoints.

    Allows specific endpoints to bypass authentication.
    """

    # Endpoints that don't require authentication
    BYPASS_PATHS = {
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/static",
        "/assets",
        "/favicon.ico",
        "/health",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Callable:
        """Process request and verify JWT token if needed."""
        # Check if this path bypasses authentication
        path = request.url.path
        if any(path.startswith(bp) for bp in self.BYPASS_PATHS):
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization header"},
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Verify token
        session_id = verify_token(token)
        if session_id is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or expired token"},
            )

        # Attach session_id to request state
        request.state.session_id = session_id

        return await call_next(request)
