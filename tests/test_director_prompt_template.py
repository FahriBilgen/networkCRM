from fortress_director.agents.base_agent import (
    PromptTemplate,
    build_prompt_path,
)


def test_director_prompt_renders_with_expected_placeholders() -> None:
    template = PromptTemplate(build_prompt_path("director_prompt.txt"))
    rendered = template.render(
        WORLD_CONTEXT="summary",
        metrics={"order": 50},
        day=1,
        turn=0,
        turn_limit=10,
        is_final_turn=False,
        flags=[],
        timeline=[],
        major_events_triggered=0,
        drama_mode=False,
        risk_budget_current=1,
        pacing="steady",
    )
    assert "steady" in rendered
