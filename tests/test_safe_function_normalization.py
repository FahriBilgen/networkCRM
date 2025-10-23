import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.orchestrator import Orchestrator
from codeaware.function_registry import FunctionCall


def test_move_npc_string_normalization_uses_keyword_arguments():
    orchestrator = Orchestrator.__new__(Orchestrator)

    normalized = orchestrator._normalize_safe_function_entries(
        ["move_npc('rhea','market')"],
        source="character:test",
    )

    assert len(normalized) == 1
    payload, metadata = normalized[0]
    assert payload["name"] == "move_npc"
    assert payload.get("kwargs") == {"npc_id": "rhea", "location": "market"}

    call = FunctionCall(
        name=payload["name"],
        args=payload.get("args", ()),
        kwargs=payload.get("kwargs", {}),
        metadata=metadata,
    )

    validated = orchestrator._validate_move_npc_call(call)
    assert validated.kwargs == {"npc_id": "rhea", "location": "market"}
