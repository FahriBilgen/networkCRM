from fortress_director.core.cluster_manager import ClusterManager
from fortress_director.core.function_registry import SafeFunctionRegistry


def build_manager() -> ClusterManager:
    registry = SafeFunctionRegistry()
    return ClusterManager.from_registry(registry)


def test_cluster_manager_returns_combat_functions_when_under_attack():
    manager = build_manager()
    context = {
        "flags": ["combat_active"],
        "metrics": {"resources": 45, "morale": 55},
        "npc_locations": [{"id": "raider", "hostile": True}],
        "recent_events": ["Skirmish erupts near the gate."],
    }
    results = manager.get_relevant_functions(context, max_count=5)
    names = {meta.name for meta in results}
    assert "apply_combat_pressure" in names or "deploy_archers" in names
    assert any(meta.category in {"combat", "structure"} for meta in results)


def test_cluster_manager_returns_economic_functions_during_shortage():
    manager = build_manager()
    context = {
        "flags": [],
        "metrics": {"resources": 10, "morale": 80},
        "recent_events": ["Caravans delayed by storms."],
    }
    results = manager.get_relevant_functions(context, max_count=6)
    names = {meta.name for meta in results}
    assert "allocate_food" in names or "gather_supplies" in names
    assert any(meta.category == "economy" for meta in results)
