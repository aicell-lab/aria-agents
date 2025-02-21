import pytest
from aria_agents.chatbot_extensions.study_suggester import create_study_suggester_function, create_create_diagram_function

@pytest.mark.asyncio
async def test_run_study_suggester(artifact_manager, config):
    study_suggester = create_study_suggester_function(config, artifact_manager)
    result = await study_suggester(user_request="I want to study the effect of osmotic stress on yeast cells")
    assert "summary_website_url" in result
    assert "error" not in result["summary_website_url"]
    assert result["summary_website_url"].startswith("http")
    # Check if the file is saved in artifact_manager
    assert await artifact_manager.exists("suggested_study.json")

@pytest.mark.asyncio
async def test_create_diagram(artifact_manager, config):
    create_diagram = create_create_diagram_function(artifact_manager)
    result = await create_diagram(suggested_study={"title": "Test Study"})
    assert "summary_website_url" in result
    assert "study_with_diagram_url" in result
    assert "error" not in result["summary_website_url"]
    assert result["summary_website_url"].startswith("http")
    assert result["study_with_diagram_url"].startswith("http")
    # Check if the file is saved in artifact_manager
    assert await artifact_manager.exists("study_with_diagram.json")
