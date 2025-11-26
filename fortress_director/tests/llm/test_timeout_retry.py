import time

import pytest

from fortress_director.llm.ollama_client import generate_with_timeout


class _SlowClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, **_: object) -> dict[str, object]:
        self.calls += 1
        time.sleep(0.05)
        return {"response": "slow"}


class _FlakyClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, **_: object) -> dict[str, object]:
        self.calls += 1
        if self.calls == 1:
            time.sleep(0.05)
        return {"response": "ok"}


def test_generate_with_timeout_retries_then_raises_timeout() -> None:
    client = _SlowClient()
    with pytest.raises(TimeoutError):
        generate_with_timeout(
            client,
            model="mock",
            prompt="ping",
            timeout_seconds=0.01,
            max_retries=1,
        )
    assert client.calls == 2


def test_generate_with_timeout_succeeds_on_retry() -> None:
    client = _FlakyClient()
    response = generate_with_timeout(
        client,
        model="mock",
        prompt="ping",
        timeout_seconds=0.01,
        max_retries=1,
    )
    assert response["response"] == "ok"
    assert client.calls == 2
