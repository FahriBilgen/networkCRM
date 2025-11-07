"""Utilities for publishing versioned API contract schemas.

The UI and SDK teams need stable JSON Schemas for the main payloads surfaced
by the game API.  This module centralises construction of those schemas so
FastAPI handlers can serve them and tests can assert against a single source
of truth.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Dict, List, Type

from pydantic import BaseModel

from fortress_director.api_models import (
    OptionModel,
    PlayerView,
    SafeFunctionResultModel,
)

JSON_SCHEMA_VERSION_URL = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_BASE_URL = "https://schemas.fortress-director.local/api"


class APIContractRegistry:
    """Lazy builder/registry for contract schemas tied to an API version."""

    def __init__(self, version: str) -> None:
        self.version = version
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._generators: Dict[str, Callable[[], Dict[str, Any]]] = {
            "player_view": lambda: _object_schema(
                PlayerView,
                schema_id=self._schema_id("player_view"),
            ),
            "options": lambda: _list_schema(
                OptionModel,
                schema_id=self._schema_id("options"),
                item_schema_id=f"{self._schema_id('options')}/item",
                title="OptionList",
            ),
            "safe_function_results": lambda: _list_schema(
                SafeFunctionResultModel,
                schema_id=self._schema_id("safe_function_results"),
                item_schema_id=f"{self._schema_id('safe_function_results')}/item",
                title="SafeFunctionResultList",
            ),
        }

    def _schema_id(self, component: str) -> str:
        return f"{SCHEMA_BASE_URL}/{self.version}/{component}"

    def list_components(self) -> List[str]:
        """Return sorted component keys."""
        return sorted(self._generators.keys())

    def get_schema(self, component: str) -> Dict[str, Any]:
        """Return a deep copy of the schema for *component*."""
        key = component.lower()

        if key not in self._generators:
            raise KeyError(f"unknown contract component: {component}")
        if key not in self._cache:
            self._cache[key] = self._generators[key]()
        return deepcopy(self._cache[key])


def _object_schema(model: Type[BaseModel], *, schema_id: str) -> Dict[str, Any]:
    """Return a JSON schema for *model* with metadata applied."""
    schema = dict(model.schema(ref_template="#/definitions/{model}"))
    definitions = schema.get("definitions")
    payload = {
        "$schema": JSON_SCHEMA_VERSION_URL,
        "$id": schema_id,
    }
    for key, value in schema.items():
        if key == "definitions":
            continue
        payload[key] = value
    if definitions:
        payload["definitions"] = definitions
    return payload


def _list_schema(
    model: Type[BaseModel],
    *,
    schema_id: str,
    item_schema_id: str,
    title: str,
) -> Dict[str, Any]:
    """Wrap the provided *model* schema inside a JSON-schema array container."""
    item_schema = dict(model.schema(ref_template="#/definitions/{model}"))
    definitions = item_schema.pop("definitions", None)
    item_schema["$id"] = item_schema_id
    schema = {
        "$schema": JSON_SCHEMA_VERSION_URL,
        "$id": schema_id,
        "title": title,
        "type": "array",
        "items": item_schema,
    }
    if definitions:
        schema["definitions"] = definitions
    return schema


__all__ = ["APIContractRegistry"]
