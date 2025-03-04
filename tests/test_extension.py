import pytest
from aria_agents.chatbot_extensions.aria_extension import get_extension

@pytest.mark.asyncio
async def test_get_extension(config):
    extensions = get_extension(config)
    
    assert len(extensions) == 1
    ext = extensions[0]
    assert ext.id == "aria"
    assert ext.name == "Aria Agent"
    assert ext.description
    assert ext.tools
    
    # Check that all required tools are present
    tool_names = set(ext.tools.keys())
    required_tools = {
        "AriaDataAnalysis",
        "AriaStudySuggester",
        "AriaStudyDiagram",
        "AriaListCorpus",
        "AriaGetCorpus",
        "AriaAddToCorpus"
    }
    assert tool_names == required_tools
    
    # Check that the tools are properly configured with event_bus
    data_analysis_tool = ext.tools["AriaDataAnalysis"]
    assert data_analysis_tool.__name__ == "explore_data"
    
    study_diagram_tool = ext.tools["AriaStudyDiagram"]
    assert study_diagram_tool.__name__ == "create_diagram"