"""Simplified test client compatible with the stub FastAPI app."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class Response:
    status_code: int
    _json: Any

    def json(self) -> Any:
        return self._json


class TestClient:
    def __init__(self, app: Any):
        self._app = app

    def post(self, path: str, json: Any | None = None) -> Response:
        result = self._app.dispatch("POST", path, json)
        return Response(status_code=200, _json=result)
