"""Interactive CLI play command for Fortress Director.

Enables real-time gameplay with:
- Ollama-generated scenes and choices
- Player interaction via console input
- Archive context injection
- Metrics display
- Save/load functionality
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from fortress_director.managers.turn_manager import TurnManager
from fortress_director.core.state_archive import StateArchive

logger = logging.getLogger(__name__)


class PlayGame:
    """Interactive game controller for Fortress Director."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        use_ollama: bool = True,
        max_turns: int = 50,
        save_dir: Optional[Path] = None,
    ):
        """Initialize game session.

        Args:
            session_id: Session name (auto-generated if None)
            use_ollama: Use Ollama agents (default) or fallback
            max_turns: Maximum turns before game ends
            save_dir: Directory for saves (default: runs/play_sessions/)
        """
        self.session_id = (
            session_id or f"play_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.max_turns = max_turns
        self.save_dir = Path(save_dir or "runs/play_sessions")
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Initialize archive and turn manager
        self.archive = StateArchive(self.session_id)
        self.turn_manager = TurnManager(use_ollama=use_ollama)
        self.turn_manager.set_archive(self.archive)

        # Game state
        self.world_state: Dict[str, Any] = {
            "threat": 0.2,
            "morale": 80,
            "resources": 100,
            "turn": 0,
        }
        self.turn_history: List[Dict[str, Any]] = []
        self.last_result: Optional[Dict[str, Any]] = None

        logger.info(
            f"Game initialized: {self.session_id} "
            f"(Ollama: {use_ollama}, Max turns: {max_turns})"
        )

    def display_scene(self, result: Dict[str, Any]) -> None:
        """Display turn result to player.

        Args:
            result: Turn result from TurnManager.execute_turn()
        """
        print("\n" + "=" * 70)
        print(f"TURN {result.get('turn', 0)}")
        print("=" * 70)

        # Scene description
        scene = result.get("scene", "The fortress awaits...")
        print(f"\n{scene}\n")

        # Display choices
        choices = result.get("choices", [])
        if choices:
            print("What do you do?")
            for choice in choices:
                choice_id = choice.get("id", "?")
                text = choice.get("text", "???")
                risk = choice.get("risk", "unknown")
                print(f"  [{choice_id}] {text} ({risk} risk)")

        # NPC reactions
        reactions = result.get("npc_reactions", [])
        if reactions:
            print("\nNPC Reactions:")
            for reaction in reactions:
                print(f"  • {reaction}")

        # World state
        print("\nFortress Status:")
        world = result.get("world", self.world_state)
        print(
            f"  Threat: {world.get('threat', 0):.1%} | "
            f"Morale: {world.get('morale', 0)}/100 | "
            f"Resources: {world.get('resources', 0)}"
        )

    def get_player_choice(
        self, choices: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Get player choice via console input.

        Args:
            choices: Available choices

        Returns:
            Selected choice dict or None if quit
        """
        valid_ids = {str(c.get("id")) for c in choices}
        valid_ids.add("q")  # Allow quit

        while True:
            try:
                choice_input = input("\nYour choice (1/2/3 or 'q' to quit): ").strip()

                if choice_input == "q":
                    return None

                if choice_input in valid_ids:
                    # Find and return choice
                    for choice in choices:
                        if str(choice.get("id")) == choice_input:
                            return choice
                    return None

                print("Invalid choice. Try again.")
            except (EOFError, KeyboardInterrupt):
                return None

    def run_turn(self) -> bool:
        """Execute single turn with player interaction.

        Returns:
            True if game continues, False if ended
        """
        turn_num = len(self.turn_history) + 1

        if turn_num > self.max_turns:
            print(
                f"\n{'='*70}\n"
                f"Maximum turns ({self.max_turns}) reached. "
                f"Campaign ended.\n"
            )
            return False

        # Determine narrative phase
        phase_pct = turn_num / self.max_turns
        if phase_pct < 0.25:
            phase = "exposition"
        elif phase_pct < 0.5:
            phase = "rising"
        elif phase_pct < 0.75:
            phase = "climax"
        else:
            phase = "resolution"

        # Execute turn via TurnManager
        try:
            result = self.turn_manager.execute_turn(self.world_state, turn_num, phase)
            self.last_result = result
        except Exception as e:
            logger.error(f"Turn execution failed: {e}")
            print(f"\nError executing turn: {e}")
            return False

        # Display scene
        self.display_scene(result)

        # Get player choice
        choices = result.get("choices", [])
        player_choice = self.get_player_choice(choices)

        if player_choice is None:
            print("\nGame ended by player.")
            return False

        # Record turn to archive
        self.world_state["threat"] = self.world_state.get("threat", 0) + 0.05
        self.world_state["morale"] = max(0, self.world_state.get("morale", 0) - 2)

        try:
            self.turn_manager.record_turn_to_archive(result, self.world_state, turn_num)
        except Exception as e:
            logger.warning(f"Failed to record turn: {e}")

        self.turn_history.append(result)
        return True

    def play_campaign(self) -> None:
        """Run full interactive campaign until player quits or max turns."""
        print(f"\n{'='*70}")
        print(f"FORTRESS DIRECTOR - Interactive Campaign")
        print(f"Session: {self.session_id}")
        print(f"Max Turns: {self.max_turns}")
        print(f"{'='*70}\n")

        try:
            while self.run_turn():
                pass
        except KeyboardInterrupt:
            print("\n\nCampaign interrupted by player.")

        self.display_final_summary()
        self.save_session()

    def display_final_summary(self) -> None:
        """Display end-of-campaign summary."""
        metrics = self.turn_manager.get_campaign_metrics()

        print(f"\n{'='*70}")
        print("CAMPAIGN SUMMARY")
        print(f"{'='*70}")
        print(f"Turns Played: {len(self.turn_history)}")
        print(f"Final Threat: {self.world_state.get('threat', 0):.1%}")
        print(f"Final Morale: {self.world_state.get('morale', 0)}/100")
        print(f"Archive Memory: {metrics.get('memory_bytes', 0)} bytes")
        ollama_status = (
            "Yes"
            if (self.last_result and self.last_result.get("used_ollama"))
            else "No (fallback)"
        )
        print(f"Ollama Used: {ollama_status}")
        print(f"{'='*70}\n")

    def save_session(self) -> None:
        """Save game session to file."""
        try:
            session_file = self.save_dir / f"{self.session_id}_session.json"

            data = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "turns_played": len(self.turn_history),
                "final_world_state": self.world_state,
                "turn_history": self.turn_history,
                "metrics": self.turn_manager.get_campaign_metrics(),
            }

            with open(session_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Session saved: {session_file}")
            print(f"Session saved: {session_file}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            print(f"Warning: Could not save session: {e}")

    @staticmethod
    def load_session(session_file: Path) -> Optional["PlayGame"]:
        """Load game session from file.

        Args:
            session_file: Path to session JSON file

        Returns:
            PlayGame instance or None if load failed
        """
        try:
            with open(session_file) as f:
                data = json.load(f)

            game = PlayGame(session_id=data.get("session_id"), use_ollama=False)
            game.world_state = data.get("final_world_state", {})
            game.turn_history = data.get("turn_history", [])

            logger.info(f"Session loaded: {session_file}")
            return game
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None


def play_command(
    session_id: Optional[str] = None,
    use_ollama: bool = True,
    max_turns: int = 50,
    load_session: Optional[Path] = None,
) -> int:
    """CLI command for interactive gameplay.

    Args:
        session_id: Optional session name
        use_ollama: Use Ollama agents
        max_turns: Maximum turns
        load_session: Load from file instead

    Returns:
        Exit code (0 = success)
    """
    try:
        if load_session:
            game = PlayGame.load_session(load_session)
            if not game:
                print(f"Failed to load session: {load_session}")
                return 1
        else:
            game = PlayGame(session_id, use_ollama, max_turns)

        game.play_campaign()
        return 0
    except Exception as e:
        logger.error(f"Game error: {e}")
        print(f"Game error: {e}")
        return 1
