#!/usr/bin/env python3
"""
Fortress Director Web Interface
"""

import sys
from pathlib import Path
import streamlit as st
import json
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fortress_director.orchestrator.orchestrator import Orchestrator

# Page configuration
st.set_page_config(
    page_title="Fortress Director",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5em;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1em;
    }
    .scene-text {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 10px 0;
    }
    .option-button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        margin: 5px;
        width: 100%;
    }
    .npc-card {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border-left: 4px solid #17a2b8;
    }
    .metric-card {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        text-align: center;
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_game_state():
    """Initialize or reset the game state in session."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = Orchestrator.build_default()
    if "turn_count" not in st.session_state:
        st.session_state.turn_count = 0
    if "game_result" not in st.session_state:
        st.session_state.game_result = None
    if "last_choice" not in st.session_state:
        st.session_state.last_choice = None


def reset_game():
    """Reset the entire game state."""
    st.session_state.orchestrator = Orchestrator.build_default()
    st.session_state.turn_count = 0
    st.session_state.game_result = None
    st.session_state.last_choice = None
    st.rerun()


def run_turn(choice_id: Optional[str] = None) -> Dict[str, Any]:
    """Run a game turn and return the result."""
    try:
        result = st.session_state.orchestrator.run_turn(player_choice_id=choice_id)
        st.session_state.turn_count += 1
        return result
    except Exception as e:
        st.error(f"Game error: {e}")
        return {}


def display_scene(result: Dict[str, Any]):
    """Display the current scene description."""
    st.markdown("## Current Scene")

    scene = result.get("scene", "")
    if scene:
        st.markdown(f'<div class="scene-text">{scene}</div>', unsafe_allow_html=True)

    # Atmosphere and sensory details
    atmosphere = result.get("atmosphere", "")
    sensory = result.get("sensory_details", "")

    col1, col2 = st.columns(2)
    with col1:
        if atmosphere:
            st.markdown(f"**Atmosphere:** {atmosphere}")
    with col2:
        if sensory:
            st.markdown(f"**Sensory:** {sensory}")


def display_character_reactions(result: Dict[str, Any]):
    """Display NPC reactions."""
    reactions = result.get("character_reactions", [])
    if reactions:
        st.markdown("## Character Reactions")
        for reaction in reactions:
            name = reaction.get("name", "Unknown")
            speech = reaction.get("speech", "")
            intent = reaction.get("intent", "")
            action = reaction.get("action", "")

            with st.expander(f"{name}", expanded=True):
                if speech:
                    st.write(f'**Says:** "{speech}"')
                if intent:
                    st.write(f"**Intent:** {intent}")
                if action:
                    st.write(f"**Action:** {action}")


def display_options(result: Dict[str, Any]):
    """Display player choice options as buttons."""
    options = result.get("options", [])
    if options:
        st.markdown("## Choose Your Action")

        # Create buttons for each option
        cols = st.columns(len(options))
        for i, (col, option) in enumerate(zip(cols, options)):
            with col:
                option_text = option.get("text", f"Option {i+1}")
                option_id = option.get("id", str(i + 1))
                if st.button(option_text, key=f"option_{i}", use_container_width=True):
                    st.session_state.last_choice = option_id  # Use actual option ID
                    st.rerun()


def display_metrics_sidebar(result: Dict[str, Any]):
    """Display game metrics in the sidebar."""
    st.sidebar.markdown("## Game Metrics")

    # Extract metrics from result or get from orchestrator
    metrics = result.get("metrics", {})

    # Display metrics as cards
    metric_items = [
        ("Order", metrics.get("order", 50)),
        ("Morale", metrics.get("morale", 50)),
        ("Resources", metrics.get("resources", 50)),
        ("Knowledge", metrics.get("knowledge", 50)),
        ("Corruption", metrics.get("corruption", 10)),
        ("Glitch", metrics.get("glitch", 10)),
    ]

    for name, value in metric_items:
        st.sidebar.markdown(
            f"""
        <div class="metric-card">
            <strong>{name}</strong><br>
            {value}
        </div>
        """,
            unsafe_allow_html=True,
        )


def display_npc_sidebar(result: Dict[str, Any]):
    """Display NPC information in the sidebar."""
    st.sidebar.markdown("## NPCs")
    # Prefer structured NPC data from the turn result (added by orchestrator). Fallback
    # to state snapshot only if structured data is not available.
    npcs = result.get("npcs")
    if not npcs:
        orchestrator = st.session_state.orchestrator
        state = orchestrator.state_store.snapshot()
        npc_locations = state.get("npc_locations", {})
        character_summary = state.get("character_summary", "")
        npcs = []
        if character_summary:
            entries = [e.strip() for e in character_summary.split(";") if e.strip()]
            for entry in entries:
                parts = entry.split()
                name = parts[0] if parts else "Unknown"
                description = " ".join(parts[1:]) if len(parts) > 1 else ""
                location = npc_locations.get(name, state.get("current_room", "Unknown"))
                npcs.append(
                    {"name": name, "description": description, "location": location}
                )

    if npcs:
        for npc in npcs:
            with st.sidebar.expander(f"{npc.get('name', 'Unknown')}", expanded=False):
                st.write(f"**Location:** {npc.get('location', 'Unknown')}")
                st.write(f"**Description:** {npc.get('description', '')}")
    else:
        st.sidebar.write("No NPC information available")


def display_win_loss(result: Dict[str, Any]):
    """Display win/loss status."""
    win_loss = result.get("win_loss", {})
    status = win_loss.get("status", "ongoing")

    if status != "ongoing":
        if status == "victory":
            st.success("Victory! You have successfully defended the fortress!")
        elif status == "defeat":
            st.error("Defeat! The fortress has fallen...")
        else:
            st.info(f"Game Ended: {win_loss.get('reason', 'Unknown reason')}")

        st.markdown(
            f"**Reason:** {win_loss.get('description', 'No description available')}"
        )


def main():
    """Main Streamlit application."""
    # Initialize game state
    initialize_game_state()

    # Header
    st.markdown(
        '<h1 class="main-header">Fortress Director</h1>', unsafe_allow_html=True
    )
    st.markdown("*A deterministic AI-powered siege defense game*")

    # Sidebar controls
    st.sidebar.markdown("## Game Controls")
    if st.sidebar.button("Reset Game", type="primary"):
        reset_game()

    if st.sidebar.button("Debug Info"):
        with st.sidebar.expander("Debug Information", expanded=True):
            st.write(f"Turn Count: {st.session_state.turn_count}")
            st.write(f"Last Choice: {st.session_state.last_choice}")
            if st.session_state.game_result:
                st.json(st.session_state.game_result)

    # Display metrics in sidebar
    if st.session_state.game_result:
        display_metrics_sidebar(st.session_state.game_result)
        display_inventory_sidebar(st.session_state.game_result)
        display_functions_sidebar(st.session_state.game_result)
        display_npc_sidebar(st.session_state.game_result)
        display_map_sidebar(st.session_state.game_result)

    # Main game area
    if st.session_state.game_result is None:
        # First turn - no choice yet
        st.session_state.game_result = run_turn()
    elif st.session_state.last_choice:
        # Player made a choice - run next turn
        choice_id = st.session_state.last_choice
        st.session_state.game_result = run_turn(choice_id)
        st.session_state.last_choice = None  # Reset for next turn

    # Display current game state
    if st.session_state.game_result:
        result = st.session_state.game_result

        # Display scene and reactions
        display_scene(result)
        display_character_reactions(result)

        # Check win/loss condition
        display_win_loss(result)

        win_loss = result.get("win_loss", {})
        if win_loss.get("status") == "ongoing":
            # Still playing - show options
            display_options(result)
        else:
            # Game ended
            st.markdown("---")
            if st.button("Play Again"):
                reset_game()


def display_functions_sidebar(result: Dict[str, Any]):
    """Display safe function calls in the sidebar."""
    st.sidebar.markdown("## AI Actions")

    # Prefer the structured safe function history if provided by the orchestrator
    safe_functions = result.get("safe_function_history") or result.get(
        "safe_function_results", []
    )

    if safe_functions:
        for func_result in safe_functions[-3:]:  # Show last 3
            func_name = func_result.get("name", "Unknown")
            func_data = func_result.get("result", {})

            with st.sidebar.expander(f"{func_name}", expanded=False):
                if isinstance(func_data, dict):
                    for key, value in func_data.items():
                        st.write(f"**{key}:** {value}")
                else:
                    st.write(str(func_data))
    else:
        st.sidebar.write("No AI actions this turn")


def display_inventory_sidebar(result: Dict[str, Any]):
    """Display inventory and items in the sidebar."""
    st.sidebar.markdown("## Inventory")

    # Get player inventory from state
    orchestrator = st.session_state.orchestrator
    state = orchestrator.state_store.snapshot()

    player = state.get("player", {})
    inventory = player.get("inventory", [])

    if inventory:
        st.sidebar.write("**Items:**")
        for item in inventory:
            st.sidebar.write(f"- {item}")
    else:
        st.sidebar.write("No items in inventory")

    # Show spawned items if any
    items = state.get("items", {})
    if items:
        st.sidebar.markdown("**World Items:**")
        for location, item_list in items.items():
            if item_list:
                st.sidebar.write(f"**{location}:** {', '.join(item_list)}")


def display_map_sidebar(result: Dict[str, Any]):
    """Display map/location information in the sidebar."""
    st.sidebar.markdown("## Map")

    # Get current room and location info from state
    orchestrator = st.session_state.orchestrator
    state = orchestrator.state_store.snapshot()

    current_room = state.get("current_room", "Unknown")
    day = state.get("day", 1)
    time = state.get("time", "Unknown")

    st.sidebar.write(f"**Current Room:** {current_room}")
    st.sidebar.write(f"**Day:** {day}")
    st.sidebar.write(f"**Time:** {time}")

    # Show recent rooms if available (prefer turn-level room_history)
    recent_events = result.get("room_history") or state.get("recent_events", [])
    if recent_events:
        st.sidebar.markdown("**Recent Locations:**")
        for event in recent_events[-2:]:  # Show last 2
            # Extract location from event text if possible
            if "entrance" in event.lower():
                st.sidebar.write("- Entrance")
            elif "wall" in event.lower():
                st.sidebar.write("- Wall")
            else:
                st.sidebar.write("- Unknown")


if __name__ == "__main__":
    main()
