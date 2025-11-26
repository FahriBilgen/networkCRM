"""TurnManager: Bridges Ollama agents with Orchestrator for Phase 9 gameplay.

Handles:
- Archive context injection to agents
- Agent initialization (Director, Planner, WorldRenderer)
- Turn execution loop with Ollama + Orchestrator
- Error handling and fallback logic
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from fortress_director.llm.ollama_adapter import (
    OllamaClient,
    OllamaAgentPipeline,
)
from fortress_director.core.state_archive import StateArchive

logger = logging.getLogger(__name__)


@dataclass
class TurnManager:
    """Orchestrates turn execution with Ollama agents."""

    ollama_client: OllamaClient = field(default_factory=OllamaClient)
    director_agent: Optional[Any] = None
    planner_agent: Optional[Any] = None
    world_renderer_agent: Optional[Any] = None
    pipeline: Optional[OllamaAgentPipeline] = None
    archive: Optional[StateArchive] = None
    use_ollama: bool = True  # Toggle to use Ollama or fallback

    def __post_init__(self):
        """Initialize Ollama agents and pipeline."""
        if not self.use_ollama:
            logger.info("Ollama disabled for this TurnManager")
            return

        # Check Ollama availability
        if not self.ollama_client.is_available():
            logger.warning("Ollama server not available at localhost:11434")
            self.use_ollama = False
            return

        try:
            # OllamaAgentPipeline handles initialization of all agents internally
            self.pipeline = OllamaAgentPipeline(self.ollama_client)
            # Extract agents from pipeline for reference
            self.director_agent = self.pipeline.director
            self.planner_agent = self.pipeline.planner
            self.world_renderer_agent = self.pipeline.renderer
            logger.info(
                "TurnManager initialized with Ollama agents (Mistral, Phi-3, Gemma)"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Ollama agents: {e}")
            self.use_ollama = False

    def set_archive(self, archive: StateArchive) -> None:
        """Set StateArchive for context injection."""
        self.archive = archive
        logger.debug("StateArchive set for TurnManager")

    def get_archive_context(self, turn: int, context_type: str = "summary") -> str:
        """Get injected context from StateArchive.

        Args:
            turn: Current turn number
            context_type: 'summary' (compressed) or 'full' (detailed)

        Returns:
            Context string to prepend to agent prompts
        """
        if not self.archive:
            return ""

        try:
            if context_type == "summary":
                context = self.archive.get_context_for_prompt(turn=turn)
            else:
                # Full context: all events since turn 0
                all_events = self.archive.get_event_extraction()
                recent_turns = self.archive.get_recent_turns_delta(n=10)
                context = f"Events: {all_events}\nRecent: {recent_turns}"
            return context
        except Exception as e:
            logger.warning(f"Failed to get archive context at turn {turn}: {e}")
            return ""

    def execute_turn(
        self,
        world_state: Dict[str, Any],
        turn_number: int,
        narrative_phase: str = "exposition",
    ) -> Dict[str, Any]:
        """Execute single turn with Ollama agents + archive context.

        Args:
            world_state: Current world/game state
            turn_number: Current turn number
            narrative_phase: One of ['exposition', 'rising', 'climax', 'resolution']

        Returns:
            Turn result with scene, choices, NPC reactions, etc.
        """
        if not self.use_ollama or not self.pipeline:
            return self._fallback_turn(world_state, turn_number, narrative_phase)

        try:
            # Get archive context
            archive_context = self.get_archive_context(turn_number)

            # Execute pipeline with Ollama agents
            result = self.pipeline.execute_turn(
                archive_context=archive_context,
                world_state=world_state,
                player_choice=None,  # Will be selected from agent-generated choices
            )

            # Enrich with turn metadata
            result["turn"] = turn_number
            result["narrative_phase"] = narrative_phase
            result["used_ollama"] = True

            logger.info(f"Turn {turn_number} executed with Ollama agents")
            return result

        except Exception as e:
            logger.error(f"Ollama turn execution failed at turn {turn_number}: {e}")
            return self._fallback_turn(world_state, turn_number, narrative_phase)

    def _fallback_turn(
        self,
        world_state: Dict[str, Any],
        turn_number: int,
        narrative_phase: str,
    ) -> Dict[str, Any]:
        """Fallback turn generation when Ollama unavailable."""
        logger.warning(
            f"Using fallback turn generation for turn {turn_number} (Ollama unavailable)"
        )
        return {
            "turn": turn_number,
            "scene": "The fortress stands resilient against the encroaching darkness.",
            "choices": [
                {"id": 1, "text": "Strengthen defenses", "risk": "low"},
                {"id": 2, "text": "Scout enemy movements", "risk": "high"},
                {"id": 3, "text": "Rally the troops", "risk": "medium"},
            ],
            "world": {"threat": world_state.get("threat", 0.5)},
            "npc_reactions": [],
            "narrative_phase": narrative_phase,
            "used_ollama": False,
        }

    def run_campaign(
        self,
        world_state: Dict[str, Any],
        turn_limit: int = 30,
        on_turn_complete: Optional[callable] = None,
    ) -> List[Dict[str, Any]]:
        """Run multi-turn campaign with Ollama agents.

        Args:
            world_state: Initial world/game state
            turn_limit: Max turns before campaign ends
            on_turn_complete: Callback after each turn (turn_number, result)

        Returns:
            List of turn results (all turns in campaign)
        """
        campaign_turns: List[Dict[str, Any]] = []
        current_state = dict(world_state)  # Copy to avoid mutation

        for turn_num in range(1, turn_limit + 1):
            # Determine narrative phase
            phase_boundaries = {
                "exposition": (1, turn_limit // 3),
                "rising": (turn_limit // 3 + 1, (2 * turn_limit) // 3),
                "climax": ((2 * turn_limit) // 3 + 1, (3 * turn_limit) // 4),
                "resolution": ((3 * turn_limit) // 4 + 1, turn_limit),
            }

            narrative_phase = "exposition"
            for phase, (start, end) in phase_boundaries.items():
                if start <= turn_num <= end:
                    narrative_phase = phase
                    break

            # Execute turn
            turn_result = self.execute_turn(current_state, turn_num, narrative_phase)

            campaign_turns.append(turn_result)

            # Update state for next turn
            if "world" in turn_result:
                current_state.update(turn_result["world"])

            # Callback
            if on_turn_complete:
                try:
                    on_turn_complete(turn_num, turn_result)
                except Exception as e:
                    logger.warning(f"Callback error at turn {turn_num}: {e}")

            logger.info(
                f"Campaign turn {turn_num}/{turn_limit} complete ({narrative_phase})"
            )

            # Check for early termination (if result indicates game over)
            if turn_result.get("game_over", False):
                logger.info(f"Campaign ended early at turn {turn_num}")
                break

        return campaign_turns

    def record_turn_to_archive(
        self,
        turn_result: Dict[str, Any],
        world_state_after: Dict[str, Any],
        turn_number: int,
    ) -> None:
        """Record turn result to StateArchive.

        Args:
            turn_result: Result dict from execute_turn()
            world_state_after: World state after turn resolution
            turn_number: Turn number for archival
        """
        if not self.archive:
            logger.debug("No archive set, skipping turn record")
            return

        try:
            # StateArchive API: record_turn(turn_number, full_state, delta)
            self.archive.record_turn(
                turn_number=turn_number,
                full_state=world_state_after,
                state_delta={"event": turn_result},
            )
            logger.debug(f"Turn {turn_number} recorded to archive")
        except Exception as e:
            logger.warning(f"Failed to record turn {turn_number} to archive: {e}")

    def get_campaign_metrics(self) -> Dict[str, Any]:
        """Get metrics from archive about current campaign.

        Returns:
            Dict with: turn_count, memory_bytes, archive_size
        """
        if not self.archive:
            return {}

        try:
            turn_count = len(self.archive.current_states) + len(
                self.archive.recent_deltas
            )

            # Calculate memory usage
            import json

            memory_bytes = sum(
                len(json.dumps(s)) for s in self.archive.current_states.values()
            )
            memory_bytes += sum(
                len(json.dumps(d)) for d in self.archive.recent_deltas.values()
            )

            return {
                "turn_count": turn_count,
                "memory_bytes": memory_bytes,
                "current_turn_states": len(self.archive.current_states),
                "recent_deltas": len(self.archive.recent_deltas),
            }
        except Exception as e:
            logger.warning(f"Failed to compute campaign metrics: {e}")
            return {}

    def reset(self) -> None:
        """Reset TurnManager for new campaign."""
        if self.archive:
            # Clear archive data for new session
            self.archive.current_states.clear()
            self.archive.recent_deltas.clear()
            self.archive.archive_summaries.clear()
            self.archive.event_log.clear()
        logger.info("TurnManager reset for new campaign")
