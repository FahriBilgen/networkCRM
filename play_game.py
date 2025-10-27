#!/usr/bin/env python3
"""Interactive Fortress Director Game Player."""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fortress_director.orchestrator.orchestrator import Orchestrator


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 80 + "\n")


def print_scene(result):
    """Print the current scene description."""
    scene = result.get("scene", "")
    if scene:
        print(f"📖 {scene}")


def print_options(result):
    """Print available player options."""
    options = result.get("options", [])
    if options:
        print("\n🎯 Available Actions:")
        for i, option in enumerate(options, 1):
            print(f"  {i}. {option.get('text', 'Unknown action')}")


def print_character_reactions(result):
    """Print NPC reactions."""
    reactions = result.get("character_reactions", [])
    if reactions:
        print("\n👥 Character Reactions:")
        for reaction in reactions:
            name = reaction.get("name", "Unknown")
            speech = reaction.get("speech", "")
            if speech:
                print(f'  💬 {name}: "{speech}"')


def print_atmosphere(result):
    """Print atmospheric description."""
    atmosphere = result.get("atmosphere", "")
    sensory = result.get("sensory_details", "")
    if atmosphere or sensory:
        print("\n🌤️  Atmosphere:")
        if atmosphere:
            print(f"  {atmosphere}")
        if sensory:
            print(f"  {sensory}")


def print_metrics(result):
    """Print current game metrics."""
    metrics = result.get("metrics", {})
    if metrics:
        print("\n📊 Current Status:")
        important_metrics = {
            "morale": "Morale",
            "order": "Order",
            "resources": "Resources",
            "knowledge": "Knowledge",
            "glitch": "System Glitch",
        }
        for key, label in important_metrics.items():
            if key in metrics:
                value = metrics[key]
                print(f"  {label}: {value}")


def print_win_loss(result):
    """Print win/loss status."""
    win_loss = result.get("win_loss", {})
    status = win_loss.get("status", "ongoing")
    if status != "ongoing":
        reason = win_loss.get("reason", "")
        description = win_loss.get("description", "")
        print(f"\n🏁 Game {status.upper()}: {reason}")
        if description:
            print(f"   {description}")


def get_player_choice(options):
    """Get player's choice from available options."""
    while True:
        try:
            choice = input("\n🎮 Your choice (number): ").strip()
            choice_num = int(choice) - 1  # Convert to 0-based index

            if 0 <= choice_num < len(options):
                selected_option = options[choice_num]
                choice_id = selected_option.get("id")
                if choice_id:
                    return choice_id
                else:
                    print("❌ Invalid option selected.")
            else:
                print(f"❌ Please enter a number between 1 and {len(options)}")

        except (ValueError, KeyboardInterrupt):
            print("❌ Please enter a valid number.")


def play_game():
    """Main interactive game loop."""
    print("🏰 Welcome to Fortress Director!")
    print("A deterministic AI-powered siege defense game.")
    print_separator()

    # Reset game state
    print("🔄 Initializing game state...")
    orchestrator = Orchestrator.build_default()

    turn_count = 0
    max_turns = 20  # Safety limit
    choice_id = None  # Initialize choice_id

    try:
        while turn_count < max_turns:
            turn_count += 1
            print(f"\n--- Turn {turn_count} ---")

            # Run turn
            result = orchestrator.run_turn(player_choice_id=choice_id)

            # Display game state
            print_scene(result)
            print_atmosphere(result)
            print_character_reactions(result)
            print_metrics(result)
            print_win_loss(result)

            # Check if game ended
            win_loss = result.get("win_loss", {})
            if win_loss.get("status") != "ongoing":
                print_separator()
                print("🎮 Game Over!")
                break

            # Get player choice for next turn
            options = result.get("options", [])
            if not options:
                print("❌ No options available.")
                print("Game might be in an error state.")
                break

            print_options(result)
            choice_id = get_player_choice(options)

            print_separator()

    except KeyboardInterrupt:
        print("\n\n👋 Game interrupted by player. Thanks for playing!")
    except Exception as e:
        print(f"\n❌ Game error: {e}")
        print("Check the logs for more details.")

    print("\n💾 Game session ended.")


if __name__ == "__main__":
    play_game()
