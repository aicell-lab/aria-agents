import pytest
from unittest.mock import patch, MagicMock
from aria_agents.chatbot_extensions.study_suggester import create_study_suggester_function, create_create_diagram_function
from tests.conftest import mock_get_query_function

@pytest.mark.asyncio
@patch("aria_agents.chatbot_extensions.study_suggester.get_query_index_dir", return_value="/mock/query_index_dir")
@patch("aria_agents.chatbot_extensions.study_suggester.get_query_function", new_callable=lambda: MagicMock(return_value=mock_get_query_function()))
async def test_run_study_suggester(mock_get_query_index_dir, mock_get_query_function, mock_artifact_manager, config, chat_input):
    study_suggester = create_study_suggester_function(config, mock_artifact_manager)
    result = await study_suggester(user_request=chat_input["question"], constraints="")
    assert "summary_website_url" in result
    assert result["summary_website_url"] == mock_artifact_manager.default_url
    assert await mock_artifact_manager.exists("suggested_study.json")
    assert await mock_artifact_manager.exists("suggested_study.html")

@pytest.mark.asyncio
async def test_create_diagram(mock_artifact_manager, suggested_study, config):
    create_diagram = create_create_diagram_function(mock_artifact_manager, config["llm_model"])
    result = await create_diagram(suggested_study=suggested_study)
    assert "summary_website_url" in result
    assert "study_with_diagram_url" in result
    assert result["summary_website_url"] == mock_artifact_manager.default_url
    assert result["study_with_diagram_url"] == mock_artifact_manager.default_url
    assert await mock_artifact_manager.exists("study_with_diagram.json")
    assert await mock_artifact_manager.exists("suggested_study.html")
