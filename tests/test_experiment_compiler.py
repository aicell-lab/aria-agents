import pytest
from aria_agents.chatbot_extensions.experiment_compiler import create_experiment_compiler_function

@pytest.mark.asyncio
async def test_run_experiment_compiler(artifact_manager, config):
    experiment_compiler = create_experiment_compiler_function(config, artifact_manager)
    result = await experiment_compiler(constraints="", max_revisions=5)
    assert "summary_website_url" in result
    assert "protocol_url" in result
    assert "error" not in result["summary_website_url"]
    assert result["summary_website_url"].startswith("http")
    assert result["protocol_url"].startswith("http")
    # Check if the file is saved in artifact_manager
    assert await artifact_manager.exists("experimental_protocol.json")
