import pytest
from aria_agents.chatbot_extensions.experiment_compiler import create_experiment_compiler_function

@pytest.mark.asyncio
async def test_run_experiment_compiler(mock_artifact_manager, config):
    experiment_compiler = create_experiment_compiler_function(config, mock_artifact_manager)
    result = await experiment_compiler(constraints="")
    assert "summary_website_url" in result
    assert "protocol_url" in result
    assert result["summary_website_url"] == "http://mock_url"
    assert result["protocol_url"] == "http://mock_url"
    # Check if the file is saved in artifact_manager