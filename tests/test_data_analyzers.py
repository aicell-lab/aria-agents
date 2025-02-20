import pytest
from aria_agents.analyzers import create_explore_data_function

@pytest.mark.asyncio
async def test_explore_data_function(artifact_manager, config):
    explore_data = create_explore_data_function(config, artifact_manager)
    result = await explore_data(data="test data", analysis_type="summary")
    assert "summary" in result
    assert isinstance(result["summary"], str)
