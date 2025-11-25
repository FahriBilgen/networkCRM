from fortress_director.narrative.demo_graph import (
    DEMO_EVENT_GRAPH,
    build_demo_graph,
)


def test_demo_graph_entry_and_final():
    g = build_demo_graph()
    assert isinstance(g, type(DEMO_EVENT_GRAPH))
    entry = g.get_node(g.entry_id)
    assert entry.id == "node_intro"
    final = g.get_node("node_final")
    assert final.is_final is True


def test_demo_graph_contains_expected_nodes() -> None:
    graph = build_demo_graph()
    assert graph.entry_id == "node_intro"
    assert len(graph.nodes) == 11
    intro = graph.get_node("node_intro")
    assert intro.next["default"] == "node_scout_activity"
    final = graph.get_node("node_final")
    assert final.is_final is True
    assert "collapse" in [tag.lower() for tag in final.tags]
