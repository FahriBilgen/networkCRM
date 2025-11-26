from typing import Any, Dict

from fortress_director.core import domain


def test_build_domain_snapshot_maps_and_syncs_npcs() -> None:
    state: Dict[str, Any] = {
        "npc_locations": [
            {
                "id": "rhea",
                "name": "Rhea",
                "role": "scout",
                "x": 1,
                "y": 2,
                "status_effects": ["alert"],
            },
        ],
    }
    snapshot = domain.build_domain_snapshot(state)
    rhea = snapshot.npcs["rhea"]
    rhea.move(x=4, y=5)
    rhea.status_effects.append("focused")
    domain.sync_npc(state, rhea)
    assert state["npc_locations"][0]["x"] == 4
    assert state["npc_locations"][0]["status_effects"][-1] == "focused"


def test_sync_structure_updates_legacy_payload() -> None:
    state: Dict[str, Any] = {
        "structures": {
            "gate": {
                "id": "gate",
                "kind": "gate",
                "integrity": 50,
                "max_integrity": 80,
            },
        },
    }
    snapshot = domain.build_domain_snapshot(state)
    structure = snapshot.structures["gate"]
    structure.reinforce(15)
    domain.sync_structure(state, structure)
    payload = state["structures"]["gate"]
    assert payload["integrity"] == 65
    assert payload["durability"] == 65
    assert payload["max_durability"] == 80


def test_append_event_marker_replaces_matching_entries() -> None:
    state: Dict[str, Any] = {
        "map_event_markers": [
            {
                "marker_id": "storm",
                "bounds": [1, 2],
                "severity": 1,
                "description": "Storm",
            },
        ],
    }
    marker = domain.EventMarker(
        id="storm", x=3, y=4, severity=2, description="Upgraded storm"
    )
    domain.append_event_marker(state, marker)
    assert state["map_event_markers"][0]["bounds"] == [3, 4]
    new_marker = domain.EventMarker(
        id="breach", x=5, y=6, severity=3, description="Wall breach"
    )
    domain.append_event_marker(state, new_marker)
    assert len(state["map_event_markers"]) == 2
