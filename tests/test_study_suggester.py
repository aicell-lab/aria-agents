import pytest
from aria_agents.chatbot_extensions.study_suggester import (
    create_study_suggester_function,
    create_diagram_function,
    create_summary_website_function,
)

@pytest.mark.asyncio
@pytest.mark.slow
async def test_run_study_suggester(config, mock_request):
    run_study_suggester = create_study_suggester_function(config)
    result = await run_study_suggester(
        user_request=mock_request,
        constraints="",
    )

    assert isinstance(result.response, str)
    assert "Study design completed successfully" in result.response
    assert "Study:" in result.response
    assert "Description:" in result.response
    assert "Hypothesis:" in result.response
    assert "Workflow:" in result.response
    assert "Materials needed:" in result.response
    assert "Expected results:" in result.response
    assert "References:" in result.response
    assert "error" not in result.response.lower()

    assert len(result.to_save) == 2
    study_file = next((f for f in result.to_save if f.name == "suggested_study.json"), None)
    website_file = next((f for f in result.to_save if f.name == "study_website.html"), None)
    assert study_file is not None
    assert website_file is not None
    assert "<html" in website_file.content.lower()

@pytest.mark.asyncio
@pytest.mark.slow
async def test_create_diagram(config, suggested_study):
    create_diagram_fn = create_diagram_function(config["llm_model"], config.get("event_bus"))
    result = await create_diagram_fn(suggested_study=suggested_study)

    assert isinstance(result.response, str)
    assert "Diagram created successfully" in result.response
    assert "error" not in result.response.lower()
    assert "graph" in result.response.lower() or "flowchart" in result.response.lower()

    assert len(result.to_save) == 1
    diagram_file = result.to_save[0]
    assert diagram_file.name == "study_with_diagram.json"
    assert "diagram_code" in diagram_file.content

@pytest.mark.asyncio
@pytest.mark.slow
async def test_create_summary_website(config):
    create_summary_fn = create_summary_website_function(config["llm_model"], config.get("event_bus"))
    result = await create_summary_fn()

    assert isinstance(result.response, str)
    assert "Summary website created successfully" in result.response
    assert "error" not in result.response.lower()

    assert len(result.to_save) == 1
    website_file = result.to_save[0]
    assert website_file.name == "study_website.html"
    assert "<html" in website_file.content.lower()
