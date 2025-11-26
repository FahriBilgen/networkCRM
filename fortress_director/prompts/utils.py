"""Prompt template helpers for Agent prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt_template(filename: str, override_path: Path | None = None) -> str:
    """Load a prompt template either from *override_path* or the prompts directory."""

    path = override_path or PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(template: str, variables: Mapping[str, str]) -> str:
    """Render *template* by replacing {{KEY}} placeholders with provided strings."""

    rendered = template
    for key, value in variables.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered
