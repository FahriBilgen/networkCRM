from fortress_director.llm.profiler import profile_llm_call


def test_profile_llm_call_success() -> None:
    payload, metrics = profile_llm_call("director", "mock-model", lambda: {"ok": True})
    assert payload == {"ok": True}
    assert metrics.success is True
    assert metrics.error_type is None
    assert metrics.agent == "director"
    assert metrics.model_name == "mock-model"


def test_profile_llm_call_failure_sets_error_type() -> None:
    def _boom() -> None:
        raise RuntimeError("llm exploded")

    payload, metrics = profile_llm_call("planner", "mock-model", _boom)
    assert payload is None
    assert metrics.success is False
    assert metrics.error_type == "RuntimeError"
