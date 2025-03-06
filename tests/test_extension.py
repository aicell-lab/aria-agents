import pytest
from aria_agents.chatbot_extensions.aria_extension import get_extension

@pytest.mark.asyncio
async def test_get_extension(config):
    extension = get_extension(config.get("event_bus"))
    
    assert extension.id == "aria"
    assert extension.name == "Aria"
    assert extension.description
    assert extension.tools
    
    # Check that all required tools are present
    tool_names = set(extension.tools.keys())
    required_tools = {
        "study_suggester",
        "experiment_compiler",
        "data_analyzer",
        "run_study_with_diagram",
        "create_summary_website",
        "list_corpus",
        "get_corpus",
        "add_to_corpus"
    }
    assert tool_names == required_tools
    
    # Check that the tools are properly configured
    data_analysis_tool = extension.tools["data_analyzer"]
    assert data_analysis_tool.__name__ == "explore_data"
    
    study_diagram_tool = extension.tools["run_study_with_diagram"]
    assert study_diagram_tool.__name__ == "create_diagram"