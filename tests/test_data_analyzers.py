import pytest
from aria_agents.chatbot_extensions.analyzers import create_explore_data


@pytest.mark.asyncio
@pytest.mark.slow
async def test_explore_data(config):
    explore_data = create_explore_data(config["llm_model"], config.get("event_bus"))
    result = await explore_data(
        explore_request="What's the average and standard deviation of all of these values?",
        data_files=[
            "mass_spectrometry_data.tsv",
            "random_file_1.csv",
            "random_file_2.csv",
        ],
        constraints="",
    )

    assert isinstance(result.to_save, list)
    assert isinstance(result.response, str)
    assert "Analysis completed successfully" in result.response
    assert "Analysis Results:" in result.response
    assert "Detailed Explanation:" in result.response
    assert "error" not in result.response.lower()

    if result.to_save:
        assert all(plot.name.endswith('.png') for plot in result.to_save)
        assert "Generated Plots:" in result.response
