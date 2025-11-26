from fortress_director.narrative.theme_graph_loader import load_event_graph_for_theme
from fortress_director.themes.loader import BUILTIN_THEMES, load_theme_from_file


def test_event_graph_loader_reads_all_builtin_themes() -> None:
    for theme_id, path in BUILTIN_THEMES.items():
        theme = load_theme_from_file(path)
        graph = load_event_graph_for_theme(theme)
        assert graph.entry_id, f"{theme_id} entry node missing"
        entry_node = graph.get_node(graph.entry_id)
        assert entry_node.id == graph.entry_id
