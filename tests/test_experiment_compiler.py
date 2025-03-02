import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import mock_get_query_function
from aria_agents.chatbot_extensions.experiment_compiler import create_experiment_compiler_function

@pytest.mark.asyncio
@patch("aria_agents.chatbot_extensions.experiment_compiler.get_query_index_dir", return_value="/mock/query_index_dir")
@patch("aria_agents.chatbot_extensions.experiment_compiler.get_query_function", new_callable=lambda: MagicMock(return_value=mock_get_query_function()))
async def test_run_experiment_compiler(mock_get_query_index_dir, mock_get_query_function, mock_artifact_manager, config):

    experiment_compiler = create_experiment_compiler_function(config, mock_artifact_manager)
    result = await experiment_compiler(constraints="", max_revisions=2)
    assert "summary_website_url" in result
    assert "protocol_url" in result
    assert result["summary_website_url"] == mock_artifact_manager.default_url
    assert result["protocol_url"] == mock_artifact_manager.default_url
    # Check if the file is saved in artifact_manager
    assert mock_artifact_manager.exists("experimental_protocol.json")
    assert mock_artifact_manager.exists("experimental_protocol.html")