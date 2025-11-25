from fortress_director.narrative.event_graph import EventNode


def test_eventnode_defaults():
    n = EventNode(id="x", description="desc")
    assert n.id == "x"
    assert n.description == "desc"
    assert isinstance(n.tags, list)
    assert isinstance(n.next, dict)
    assert n.is_final is False


def test_event_node_defaults_are_isolated() -> None:
    node_a = EventNode(id="intro", description="Opening")
    node_b = EventNode(id="breach", description="Breach", tags=["battle"])
    node_a.tags.append("setup")
    node_a.next["default"] = "breach"

    assert node_a.tags == ["setup"]
    assert node_b.tags == ["battle"]
    assert node_a.next == {"default": "breach"}
    assert node_b.next == {}
    assert node_a.is_final is False


def test_event_node_can_mark_final() -> None:
    node = EventNode(id="finale", description="The siege ends.", is_final=True)
    assert node.is_final is True
    assert node.tags == []
