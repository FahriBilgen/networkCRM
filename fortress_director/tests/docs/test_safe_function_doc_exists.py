from __future__ import annotations

from pathlib import Path


DOC_DIR = Path(__file__).resolve().parents[3] / "docs" / "safe_functions"


def test_safe_function_docs_exist() -> None:
    expected = [
        DOC_DIR / "catalog.md",
        DOC_DIR / "combat.md",
        DOC_DIR / "structure.md",
        DOC_DIR / "economy.md",
        DOC_DIR / "morale.md",
        DOC_DIR / "npc.md",
        DOC_DIR / "event.md",
        DOC_DIR / "utility.md",
    ]
    for doc in expected:
        assert doc.is_file(), f"missing doc: {doc}"
        assert doc.read_text(encoding="utf-8").strip()
