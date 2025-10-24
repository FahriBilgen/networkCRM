"""A lightweight stub implementation of key FastAPI features used in tests."""
from __future__ import annotations
from typing import Any, Callable, Dict, Tuple

RouteKey = Tuple[str, str]


def Body(default: Any = ..., embed: bool = False) -> Any:
    """Return the provided default value.

    The real FastAPI Body function provides metadata for request parsing. For
    testing we simply propagate the default value so function signatures behave
    as expected when invoked directly.
    """

    return default


class FastAPI:
    """A very small subset of the FastAPI application interface."""

    def __init__(self) -> None:
        self._routes: Dict[RouteKey, Callable[..., Any]] = {}

    def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a handler for POST requests to *path*."""

        method = "POST"

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._routes[(method, path)] = func
            return func

        return decorator

    def dispatch(self, method: str, path: str, payload: Any) -> Any:
        """Invoke the handler registered for *method* and *path*."""

        key: RouteKey = (method.upper(), path)
        if key not in self._routes:
            raise KeyError(f"No route registered for {method} {path}")

        handler = self._routes[key]
        if payload is None:
            return handler()
        if isinstance(payload, dict):
            return handler(**payload)
        return handler(payload)


__all__ = ["FastAPI", "Body"]
