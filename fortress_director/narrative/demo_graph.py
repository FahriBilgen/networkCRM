"""Canonical demo event graph definition."""

from __future__ import annotations

from typing import Dict

from .event_graph import EventGraph, EventNode


def build_demo_graph() -> EventGraph:
    """Return the handcrafted demo event graph used by default pipelines."""

    nodes: Dict[str, EventNode] = {
        "node_intro": EventNode(
            id="node_intro",
            description="Scouts report storm-front movement while commanders brief the garrison.",
            tags=["hope", "tension"],
            next={
                "default": "node_scout_activity",
                "breach_warning": "node_minor_breach",
            },
        ),
        "node_scout_activity": EventNode(
            id="node_scout_activity",
            description="Forward riders shadow raider patrols probing the outer dunes.",
            tags=["recon", "tension"],
            next={
                "default": "node_minor_breach",
                "enemy_mass": "node_major_assault",
                "saboteur_sighting": "node_sabotage",
            },
        ),
        "node_minor_breach": EventNode(
            id="node_minor_breach",
            description="A splinter squad claws through a service tunnel forcing quick containment.",
            tags=["battle", "tension"],
            next={
                "default": "node_reinforcement",
                "supply_chain": "node_sabotage",
            },
        ),
        "node_sabotage": EventNode(
            id="node_sabotage",
            description="Depth charges rock the cisterns as infiltrators test the fortress interior.",
            tags=["sabotage", "tension"],
            next={
                "default": "node_reinforcement",
                "morale_risk": "node_escape_plan",
            },
        ),
        "node_reinforcement": EventNode(
            id="node_reinforcement",
            description="Convoys from the desert flank arrive with engineers and morale banners.",
            tags=["hope", "logistics"],
            next={
                "default": "node_major_assault",
                "pressure_spike": "node_wall_collapse",
            },
        ),
        "node_major_assault": EventNode(
            id="node_major_assault",
            description="Siege towers and beast batteries push toward the charred western wall.",
            tags=["battle", "escalation"],
            next={
                "default": "node_wall_collapse",
                "heroic_charge": "node_last_stand",
            },
        ),
        "node_wall_collapse": EventNode(
            id="node_wall_collapse",
            description="The old rampart buckles, dumping rubble and defenders onto the inner keep.",
            tags=["collapse", "battle"],
            next={
                "default": "node_last_stand",
                "civilian_panic": "node_escape_plan",
            },
        ),
        "node_last_stand": EventNode(
            id="node_last_stand",
            description="Shield walls tighten around the relic vault as commanders vow to hold.",
            tags=["battle", "despair"],
            next={
                "default": "node_escape_plan",
                "diplomatic_opening": "node_negotiation",
            },
        ),
        "node_escape_plan": EventNode(
            id="node_escape_plan",
            description="Tunnels below the kitchens are mapped for a potential exodus.",
            tags=["hope", "sabotage"],
            next={
                "default": "node_negotiation",
                "total_collapse": "node_final",
            },
        ),
        "node_negotiation": EventNode(
            id="node_negotiation",
            description="Envoys meet under white banners to stall for reinforcements.",
            tags=["hope", "tension"],
            next={
                "default": "node_final",
                "betrayal": "node_last_stand",
            },
        ),
        "node_final": EventNode(
            id="node_final",
            description="Either surrender terms or evacuation efforts decide the fortress fate.",
            tags=["collapse"],
            next={},
            is_final=True,
        ),
    }
    return EventGraph(nodes, entry_id="node_intro")


DEMO_EVENT_GRAPH = build_demo_graph()

__all__ = ["build_demo_graph", "DEMO_EVENT_GRAPH"]
