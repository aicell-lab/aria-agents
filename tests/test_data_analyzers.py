import pytest
from aria_agents.chatbot_extensions.analyzers import create_explore_data


@pytest.mark.asyncio
@pytest.mark.slow
async def test_explore_data(mock_artifact_manager, config):
    explore_data = create_explore_data(mock_artifact_manager, config["llm_model"])
    result = await explore_data(
        explore_request="What's the average and standard deviation of all of these values?",
        data_files=[
            "mass_spectrometry_data.tsv",
            "random_file_1.csv",
            "random_file_2.csv",
        ],
        constraints="",
    )

    assert isinstance(result, dict)
    assert "data_analysis_agent_final_response" in result
    assert "data_analysis_agent_final_explanation" in result
    assert "plot_urls" in result
    assert isinstance(result["data_analysis_agent_final_response"], str)
    assert "error" not in result["data_analysis_agent_final_response"].lower()
    assert isinstance(result["data_analysis_agent_final_explanation"], str)
    assert isinstance(result["plot_urls"], dict)
    for url in result["plot_urls"].values():
        assert url == mock_artifact_manager.default_url
