import pytest
from unittest.mock import patch
from aria_agents.utils import create_query_function
from aria_agents.chatbot_extensions.experiment_compiler import create_experiment_compiler_function

@pytest.mark.asyncio
@patch("aria_agents.chatbot_extensions.experiment_compiler.get_query_function")
@patch("aria_agents.chatbot_extensions.experiment_compiler.get_query_index_dir")
async def test_run_experiment_compiler(mock_get_query_index_dir, mock_get_query_function, mock_artifact_manager, config):
    query_response = {
        "response": "This is a mock response for the query.",
        "source_nodes": [
            {"metadata": {"URL": "http://example.com/article1"}},
            {"metadata": {"URL": "http://example.com/article2"}},
        ],
    }
    mock_get_query_index_dir.return_value = "/mock/query_index_dir"
    mock_get_query_function.return_value = lambda query_index_dir, config: create_query_function(lambda query, config=config: query_response)

    experiment_compiler = create_experiment_compiler_function(config, mock_artifact_manager)
    result = await experiment_compiler(constraints="", max_revisions=5)
    assert "summary_website_url" in result
    assert "protocol_url" in result
    assert result["summary_website_url"] == mock_artifact_manager.default_url
    assert result["protocol_url"] == mock_artifact_manager.default_url
    # Check if the file is saved in artifact_manager
    assert mock_artifact_manager.exists("experimental_protocol.json")
    assert mock_artifact_manager.exists("experimental_protocol.html")