from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_DIR = REPO_ROOT / "demo_build"


def _read(relative: str) -> str:
    path = DEMO_DIR / relative
    assert path.is_file(), f"{relative} is missing"
    return path.read_text(encoding="utf-8")


def test_run_wrappers_exist() -> None:
    for name in ("run_demo.sh", "run_demo.ps1"):
        path = DEMO_DIR / name
        assert path.is_file(), f"{name} should exist"
        assert path.stat().st_size > 0


@pytest.mark.parametrize(
    ("script", "markers"),
    [
        (
            "setup_demo.sh",
            [
                "pip install -r",
                "npm run build",
            ],
        ),
        (
            "setup_demo.ps1",
            [
                "pip install -r",
                "npm run build",
            ],
        ),
    ],
)
def test_setup_scripts_include_required_steps(script: str, markers: list[str]) -> None:
    content = _read(script)
    for marker in markers:
        assert marker in content, f"{script} missing marker: {marker}"
