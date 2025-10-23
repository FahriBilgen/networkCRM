"""Validation utilities for registry-backed function calls."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .function_registry import (
    FunctionCall,
    FunctionNotRegisteredError,
    FunctionValidationError,
    SafeFunctionRegistry,
)


class RateLimitExceeded(FunctionValidationError):
    """Raised when a rate limit for safe functions is exceeded."""


@dataclass(frozen=True)
class ValidationResult:
    """Structured response returned by the validator."""

    success: bool
    message: str = ""
    call: FunctionCall | None = None


class FunctionCallValidator:
    """Validate proposed function calls against the safe registry."""

    def __init__(
        self,
        registry: SafeFunctionRegistry,
        *,
        max_calls_per_function: int | None = None,
        max_total_calls: int | None = None,
    ) -> None:
        self._registry = registry
        self._max_calls_per_function = max_calls_per_function
        self._max_total_calls = max_total_calls
        self._per_function: Counter[str] = Counter()
        self._total_calls = 0

    def reset(self) -> None:
        """Reset all counters, e.g., between turns."""

        self._per_function.clear()
        self._total_calls = 0

    @property
    def registry(self) -> SafeFunctionRegistry:
        """Expose the underlying safe function registry."""

        return self._registry

    def validate(self, payload: Dict[str, Any]) -> FunctionCall:
        """Validate and return a sanitized FunctionCall or raise."""

        call = self._coerce_call(payload)
        self._enforce_rate_limits(call.name)
        validated = self._registry.validate(call)
        self._record_success(validated.name)
        return validated

    def validate_call(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Convenience wrapper returning ``(success, message)``."""

        try:
            self.validate(payload)
        except (FunctionNotRegisteredError, FunctionValidationError) as exc:
            return False, str(exc)
        except Exception as exc:  # pragma: no cover - defensive guard
            return False, str(exc)
        return True, ""

    def revert_record(self, name: str) -> None:
        """Roll back counters when a validated call ultimately fails."""

        if self._total_calls > 0:
            self._total_calls -= 1
        if self._per_function[name] > 0:
            self._per_function[name] -= 1

    def _coerce_call(self, payload: Dict[str, Any]) -> FunctionCall:
        if not isinstance(payload, dict):
            raise FunctionValidationError(
                "Function call payload must be a dict"
            )
        if "name" not in payload:
            raise FunctionValidationError(
                "Function call payload missing 'name'"
            )

        args = payload.get("args", ())
        kwargs = payload.get("kwargs", {})
        metadata = payload.get("metadata", {})
        if not isinstance(args, (list, tuple)):
            raise FunctionValidationError(
                "Function call 'args' must be a list or tuple"
            )
        if not isinstance(kwargs, dict):
            raise FunctionValidationError(
                "Function call 'kwargs' must be a mapping"
            )
        if not isinstance(metadata, dict):
            raise FunctionValidationError(
                "Function call 'metadata' must be a mapping"
            )

        return FunctionCall(
            name=str(payload["name"]).strip(),
            args=tuple(args),
            kwargs=dict(kwargs),
            metadata=dict(metadata),
        )

    def _enforce_rate_limits(self, name: str) -> None:
        if (
            self._max_total_calls is not None
            and self._total_calls >= self._max_total_calls
        ):
            raise RateLimitExceeded(
                "Global function call rate limit exceeded"
            )
        if self._max_calls_per_function is not None:
            if self._per_function[name] >= self._max_calls_per_function:
                raise RateLimitExceeded(
                    f"Rate limit exceeded for function '{name}'"
                )

    def _record_success(self, name: str) -> None:
        """Record a successful validation for rate-limiting purposes."""

        self._total_calls += 1
        self._per_function[name] += 1
