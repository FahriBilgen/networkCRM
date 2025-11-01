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
        import sys
        import logging

        self._logger = getattr(self, "_logger", logging.getLogger(__name__))
        self._logger.info(f"Validating function call payload: {payload}")
        try:
            call = self._coerce_call(payload)
            self._logger.debug(f"Coerced call: {call}")
            self._enforce_rate_limits(call.name)
            validated = self._registry.validate(call)
            self._record_success(validated.name)
            self._logger.info(
                f"Function call '{validated.name}' validated successfully."
            )
            return validated
        except (FunctionNotRegisteredError, FunctionValidationError) as exc:
            self._logger.warning(f"Function validation failed: {exc}")
            print(f"[ALERT] Function validation failed: {exc}", file=sys.stderr)
            raise
        except Exception as exc:
            self._logger.error(
                f"Unexpected error during function validation: {exc}", exc_info=True
            )
            print(
                f"[CRITICAL] Unexpected error during function validation: {exc}",
                file=sys.stderr,
            )
            raise

    def validate_call(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Convenience wrapper returning ``(success, message)``."""
        import sys
        import logging

        self._logger = getattr(self, "_logger", logging.getLogger(__name__))
        self._logger.info(f"validate_call invoked for payload: {payload}")
        try:
            self.validate(payload)
        except (FunctionNotRegisteredError, FunctionValidationError) as exc:
            self._logger.warning(f"validate_call failed: {exc}")
            print(f"[ALERT] validate_call failed: {exc}", file=sys.stderr)
            return False, str(exc)
        except Exception as exc:  # pragma: no cover - defensive guard
            self._logger.error(f"validate_call critical error: {exc}", exc_info=True)
            print(f"[CRITICAL] validate_call critical error: {exc}", file=sys.stderr)
            return False, str(exc)
        self._logger.info("validate_call succeeded.")
        return True, ""

    def revert_record(self, name: str) -> None:
        """Roll back counters when a validated call ultimately fails."""
        import logging

        self._logger = getattr(self, "_logger", logging.getLogger(__name__))
        self._logger.info(f"Reverting record for function: {name}")
        if self._total_calls > 0:
            self._total_calls -= 1
        if self._per_function[name] > 0:
            self._per_function[name] -= 1
        self._logger.debug(
            f"Counters after revert: total={{self._total_calls}}, per_function={{self._per_function}}"
        )

    def _coerce_call(self, payload: Dict[str, Any]) -> FunctionCall:
        import sys
        import logging

        self._logger = getattr(self, "_logger", logging.getLogger(__name__))
        self._logger.debug(f"Coercing function call from payload: {payload}")
        if not isinstance(payload, dict):
            self._logger.error("Function call payload must be a dict")
            print("[CRITICAL] Function call payload must be a dict", file=sys.stderr)
            raise FunctionValidationError("Function call payload must be a dict")
        if "name" not in payload:
            self._logger.error("Function call payload missing 'name'")
            print("[CRITICAL] Function call payload missing 'name'", file=sys.stderr)
            raise FunctionValidationError("Function call payload missing 'name'")

        args = payload.get("args", ())
        kwargs = payload.get("kwargs", {})
        metadata = payload.get("metadata", {})
        if not isinstance(args, (list, tuple)):
            self._logger.error("Function call 'args' must be a list or tuple")
            print(
                "[CRITICAL] Function call 'args' must be a list or tuple",
                file=sys.stderr,
            )
            raise FunctionValidationError(
                "Function call 'args' must be a list or tuple"
            )
        if not isinstance(kwargs, dict):
            self._logger.error("Function call 'kwargs' must be a mapping")
            print(
                "[CRITICAL] Function call 'kwargs' must be a mapping", file=sys.stderr
            )
            raise FunctionValidationError("Function call 'kwargs' must be a mapping")
        if not isinstance(metadata, dict):
            self._logger.error("Function call 'metadata' must be a mapping")
            print(
                "[CRITICAL] Function call 'metadata' must be a mapping", file=sys.stderr
            )
            raise FunctionValidationError("Function call 'metadata' must be a mapping")

        call = FunctionCall(
            name=str(payload["name"]).strip(),
            args=tuple(args),
            kwargs=dict(kwargs),
            metadata=dict(metadata),
        )
        self._logger.debug(f"Coerced FunctionCall: {call}")
        return call

    def _enforce_rate_limits(self, name: str) -> None:
        import sys
        import logging

        self._logger = getattr(self, "_logger", logging.getLogger(__name__))
        self._logger.debug(f"Enforcing rate limits for function: {name}")
        if (
            self._max_total_calls is not None
            and self._total_calls >= self._max_total_calls
        ):
            self._logger.warning("Global function call rate limit exceeded")
            print("[ALERT] Global function call rate limit exceeded", file=sys.stderr)
            raise RateLimitExceeded("Global function call rate limit exceeded")
        if self._max_calls_per_function is not None:
            if self._per_function[name] >= self._max_calls_per_function:
                self._logger.warning(f"Rate limit exceeded for function '{name}'")
                print(
                    f"[ALERT] Rate limit exceeded for function '{name}'",
                    file=sys.stderr,
                )
                raise RateLimitExceeded(f"Rate limit exceeded for function '{name}'")

    def _record_success(self, name: str) -> None:
        """Record a successful validation for rate-limiting purposes."""
        import logging

        self._logger = getattr(self, "_logger", logging.getLogger(__name__))
        self._total_calls += 1
        self._per_function[name] += 1
        self._logger.debug(
            f"Recorded success for function: {name} (total_calls={self._total_calls}, per_function={self._per_function[name]})"
        )
