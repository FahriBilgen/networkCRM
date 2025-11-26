import json

import pytest

from fortress_director.llm import ollama_client
from fortress_director.llm.ollama_client import OllamaClient, OllamaClientError


class _DummyResp:
    def __init__(self, body_bytes: bytes):
        self._body = body_bytes

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _make_urlopen_mock(body: bytes):
    def _mock(req, timeout=None):
        return _DummyResp(body)

    return _mock


def test_list_models_parses_data_list(monkeypatch):
    payload = {"object": "list", "data": [{"id": "m1"}, {"id": "m2"}]}
    body = json.dumps(payload).encode("utf-8")
    monkeypatch.setattr(ollama_client.request, "urlopen", _make_urlopen_mock(body))

    client = OllamaClient()
    models = client.list_models()
    assert sorted(models) == ["m1", "m2"]


def test_list_models_parses_list_shape(monkeypatch):
    payload = [{"model": "alpha"}, {"name": "beta"}]
    body = json.dumps(payload).encode("utf-8")
    monkeypatch.setattr(ollama_client.request, "urlopen", _make_urlopen_mock(body))

    client = OllamaClient()
    models = client.list_models()
    assert sorted(models) == ["alpha", "beta"]


def test_list_models_invalid_json_raises(monkeypatch):
    # Return invalid JSON
    body = b"not-a-json"
    monkeypatch.setattr(ollama_client.request, "urlopen", _make_urlopen_mock(body))

    client = OllamaClient()
    with pytest.raises(OllamaClientError):
        client.list_models()


import json
import types

import pytest

from fortress_director.llm import ollama_client
from fortress_director.llm.ollama_client import OllamaClient, OllamaClientError
import json
import types

import pytest

from fortress_director.llm import ollama_client
from fortress_director.llm.ollama_client import OllamaClient, OllamaClientError


class _DummyResp:
    def __init__(self, body_bytes: bytes):
        self._body = body_bytes

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        import json
        import pytest

        from fortress_director.llm import ollama_client
        from fortress_director.llm.ollama_client import OllamaClient, OllamaClientError

        class _DummyResp:
            def __init__(self, body_bytes: bytes):
                self._body = body_bytes

            def read(self) -> bytes:
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        def _make_urlopen_mock(body: bytes):
            def _mock(req, timeout=None):
                return _DummyResp(body)

            return _mock

        def test_list_models_parses_data_list(monkeypatch):
            payload = {"object": "list", "data": [{"id": "m1"}, {"id": "m2"}]}
            body = json.dumps(payload).encode("utf-8")
            monkeypatch.setattr(
                ollama_client.request, "urlopen", _make_urlopen_mock(body)
            )

            client = OllamaClient()
            models = client.list_models()
            assert sorted(models) == ["m1", "m2"]

        def test_list_models_parses_list_shape(monkeypatch):
            payload = [{"model": "alpha"}, {"name": "beta"}]
            body = json.dumps(payload).encode("utf-8")
            monkeypatch.setattr(
                ollama_client.request, "urlopen", _make_urlopen_mock(body)
            )

            client = OllamaClient()
            models = client.list_models()
            assert sorted(models) == ["alpha", "beta"]

        def test_list_models_invalid_json_raises(monkeypatch):
            # Return invalid JSON
            body = b"not-a-json"
            monkeypatch.setattr(
                ollama_client.request, "urlopen", _make_urlopen_mock(body)
            )

            client = OllamaClient()
            with pytest.raises(OllamaClientError):
                client.list_models()
