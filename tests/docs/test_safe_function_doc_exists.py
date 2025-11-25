from pathlib import Path


def test_safe_function_catalog_exists():
    p = Path("docs/safe_functions/catalog.md")
    assert p.exists(), "catalog.md for safe_functions must exist"
    text = p.read_text(encoding="utf-8")
    assert "Safe Function Catalog" in text
