"""Compatibility wrapper re-exporting the Fortress Director orchestrator."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fortress_director.orchestrator.orchestrator import (
    DEFAULT_WORLD_STATE,
    Orchestrator,
    RELATIONSHIP_SUMMARY_DEFAULT,
    StateStore,
)

__all__ = [
    "DEFAULT_WORLD_STATE",
    "Orchestrator",
    "RELATIONSHIP_SUMMARY_DEFAULT",
    "StateStore",
    "simulate",
]


def simulate(player_choice_id: Optional[str] = None) -> Dict[str, Any]:
    """Run a single turn using default wiring; kept for legacy callers."""

    orchestrator = Orchestrator.build_default()
    return orchestrator.run_turn(player_choice_id=player_choice_id)
