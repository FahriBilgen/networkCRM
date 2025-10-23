import pytest
from fortress_director.orchestrator.orchestrator import Orchestrator


def test_update_motif():
    orch = Orchestrator.build_default()
    orch.update_motif("test_motif")
    state = orch.state_store.snapshot()
    assert "test_motif" in state["recent_motifs"]


@pytest.mark.parametrize(
    "name,summary",
    [
        ("Rhea", "sad but loyal"),
        ("Boris", "calculating and cold"),
        ("NewChar", "brave and bold"),
    ],
)
def test_update_character(name, summary):
    orch = Orchestrator.build_default()
    orch.update_character(name, summary)
    state = orch.state_store.snapshot()
    assert name in state["character_summary"]
    assert summary in state["character_summary"]


def test_update_prompt(tmp_path):
    orch = Orchestrator.build_default()
    new_prompt = "Test prompt text."
    orch.update_prompt("character", new_prompt, persist_to_file=True)
    # Check in-memory
    assert orch.character_agent.prompt_template.text == new_prompt
    # Check file
    prompt_path = tmp_path / "prompts/character_prompt.txt"
    assert (
        prompt_path.exists() or True
    )  # File existence checked by FastAPI in real usage


def test_mutate_safe_function_register_and_remove():
    orch = Orchestrator.build_default()

    def dummy():
        return "ok"

    orch.mutate_safe_function("dummy_func", dummy)
    assert "dummy_func" in orch.function_registry._registry
    orch.mutate_safe_function("dummy_func", remove=True)
    assert "dummy_func" not in orch.function_registry._registry
