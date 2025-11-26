from fortress_director.core.function_registry import SafeFunctionRegistry


def test_default_metadata_catalog_exposes_new_schema():
    registry = SafeFunctionRegistry()
    metadata = list(registry.list_metadata())
    assert len(metadata) >= 65
    names = {meta.name for meta in metadata}
    assert "reinforce_wall" in names
    assert "move_npc" in names


def test_selected_entries_have_expected_categories():
    registry = SafeFunctionRegistry()
    reinforce = registry.get_metadata("reinforce_wall")
    assert reinforce is not None
    assert reinforce.category == "structure"
    assert any(param.name == "structure_id" for param in reinforce.params)
    inspire = registry.get_metadata("inspire_troops")
    assert inspire is not None
    assert inspire.category == "morale"
