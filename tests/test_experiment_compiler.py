import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import mock_get_query_function
from aria_agents.chatbot_extensions.experiment_compiler import create_experiment_compiler_function

@pytest.mark.slow
@pytest.mark.asyncio
@patch("aria_agents.chatbot_extensions.experiment_compiler.get_query_index_dir", return_value="/mock/query_index_dir")
@patch("aria_agents.chatbot_extensions.experiment_compiler.get_query_function", new_callable=lambda: MagicMock(return_value=mock_get_query_function()))
async def test_run_experiment_compiler(mock_get_query_index_dir, mock_get_query_function, config):
    experiment_compiler = create_experiment_compiler_function(config)
    result = await experiment_compiler(constraints="", max_revisions=2)
    
    assert "to_save" in result
    assert "response" in result
    assert "protocol_title" in result.response
    assert "sections" in result.response
    assert isinstance(result.to_save, list)
    assert len(result.to_save) > 0
    assert result.to_save[0].name == "experimental_protocol.json"
    assert result.to_save[1].name == "experimental_protocol.html"