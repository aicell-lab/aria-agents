import pytest
from aria_agents.chatbot_extensions.study_suggester import create_study_suggester_function, create_create_diagram_function

@pytest.mark.asyncio
async def test_run_study_suggester(mock_artifact_manager, config, chat_input):
    study_suggester = create_study_suggester_function(config, mock_artifact_manager)
    result = await study_suggester(user_request=chat_input["question"], constraints="")
    # TODO: assert "error" not in result["summary_website_url"]
    assert "summary_website_url" in result
    assert result["summary_website_url"] == mock_artifact_manager.default_url
    # Check if the file is saved in artifact_manager
    assert await mock_artifact_manager.exists("suggested_study.json")
    assert await mock_artifact_manager.exists("suggested_study.html")

@pytest.mark.asyncio
async def test_create_diagram(mock_artifact_manager, suggested_study, config):
    create_diagram = create_create_diagram_function(mock_artifact_manager, config["llm_model"])
    result = await create_diagram(suggested_study=suggested_study)
    # TODO: assert "error" not in result["summary_website_url"]
    assert "summary_website_url" in result
    assert "study_with_diagram_url" in result
    assert result["summary_website_url"] == mock_artifact_manager.default_url
    assert result["study_with_diagram_url"] == mock_artifact_manager.default_url
    # Check if the file is saved in mock_artifact_manager
    assert await mock_artifact_manager.exists("study_with_diagram.json")
    assert await mock_artifact_manager.exists("suggested_study.html")
