from __future__ import annotations

from pathlib import Path


def test_demo_overview_document_exists() -> None:
    doc_path = Path(__file__).resolve().parents[3] / "docs" / "demo_overview.md"
    assert doc_path.is_file()
    assert doc_path.read_text(encoding="utf-8").strip()
