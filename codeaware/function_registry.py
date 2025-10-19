from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional

LOGGER = logging.getLogger(__name__)
"""Code-aware registry for deterministic, validator-backed function calls."""


Validator = Callable[["FunctionCall"], Optional["FunctionCall"]]


class FunctionRegistryError(RuntimeError):
    """Base exception for registry failures."""


class FunctionAlreadyRegisteredError(FunctionRegistryError):
    """Raised when attempting to register a duplicate function name."""


class FunctionNotRegisteredError(FunctionRegistryError):
    """Raised when a requested function name is unknown to the registry."""


class FunctionValidationError(FunctionRegistryError):
    """Raised when validation fails for a safe function call."""


@dataclass
class FunctionCall:
    """Structured representation of a proposed function call."""

    name: str
    args: tuple[Any, ...] = ()
    kwargs: Dict[str, Any] | None = None
    metadata: Dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise FunctionValidationError("Function name must be a non-empty string")
        self.args = tuple(self.args or ())
        self.kwargs = dict(self.kwargs or {})
        self.metadata = dict(self.metadata or {})


@dataclass
class RegisteredFunction:
    """Payload stored for each registered safe function."""

    name: str
    function: Callable[..., Any]
    validator: Validator


class SafeFunctionRegistry:
    """Manage registered functions backed by validation callbacks."""

    def __init__(self) -> None:
        self._functions: Dict[str, RegisteredFunction] = {}

    def register(
        self,
        name: str,
        function: Callable[..., Any],
        validator: Optional[Validator] = None,
    ) -> None:
        """Register a new safe function with an optional validator."""
        LOGGER.info("Registering safe function: %s", name)
        if name in self._functions:
            LOGGER.error("Function '%s' already registered", name)
            raise FunctionAlreadyRegisteredError(
                f"Function '{name}' already registered"
            )
        if not callable(function):  # pragma: no cover - defensive guard
            LOGGER.error("Provided function for '%s' is not callable", name)
            raise FunctionRegistryError("Provided function must be callable")
        wrapped_validator = validator or self._default_validator
        self._functions[name] = RegisteredFunction(
            name=name,
            function=function,
            validator=wrapped_validator,
        )
        LOGGER.info("Safe function '%s' registered successfully.", name)

    def unregister(self, name: str) -> None:
        """Remove a function from the registry if present."""

        self._functions.pop(name, None)

    def clear(self) -> None:
        """Remove all registered functions."""

        self._functions.clear()

    def is_registered(self, name: str) -> bool:
        """Return whether the given function name is known."""

        return name in self._functions

    def list_functions(self) -> Iterable[str]:
        """Yield registered function names in registration order."""

        return tuple(self._functions.keys())

    def validate(self, call: FunctionCall) -> FunctionCall:
        """Run the associated validator for the provided call."""
        LOGGER.info("Validating function call: %s", call.name)
        entry = self._require(call.name)
        validated = entry.validator(call) or call
        if not isinstance(validated, FunctionCall):
            raise FunctionValidationError(
                f"Validator for '{call.name}' must return a FunctionCall"
            )
        if validated.name != call.name:
            raise FunctionValidationError("Validator cannot mutate the function name")
        return validated

    def call(
        self,
        name_or_call: str | FunctionCall,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Validate and execute a registered function."""
        call = (
            name_or_call
            if isinstance(name_or_call, FunctionCall)
            else FunctionCall(name=str(name_or_call), args=args, kwargs=kwargs)
        )
        LOGGER.info("Calling safe function: %s", call.name)
        validated = self.validate(call)
        entry = self._require(validated.name)
        LOGGER.info(
            "Executing function '%s' with args=%s kwargs=%s",
            validated.name,
            validated.args,
            validated.kwargs,
        )
        result = entry.function(*validated.args, **validated.kwargs)
        LOGGER.info(
            "Function '%s' executed, result: %s",
            validated.name,
            result,
        )
        return result

    def get(self, name: str) -> RegisteredFunction:
        """Return the registered descriptor for a function."""
        LOGGER.info("Getting registered function: %s", name)
        return self._require(name)

    def _require(self, name: str) -> RegisteredFunction:
        try:
            return self._functions[name]
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise FunctionNotRegisteredError(
                f"Function '{name}' is not registered"
            ) from exc

    @staticmethod
    def _default_validator(call: FunctionCall) -> FunctionCall:
        """Default validator that simply echoes the original call."""

        return call
