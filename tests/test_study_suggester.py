import pytest
from aria_agents.chatbot_extensions.aux import SuggestedStudy
from aria_agents.chatbot_extensions.study_suggester import (
    create_study_suggester_function,
    create_diagram_function,
    create_summary_website_function,
    StudyWithDiagram,
    StudyDiagram,
)

@pytest.fixture
def mock_request():
    return "I want to study the effect of osmotic stress on yeast cells"

@pytest.mark.asyncio
@pytest.mark.slow
async def test_run_study_suggester(config, mock_request):
    run_study_suggester = create_study_suggester_function(config)
    result = await run_study_suggester(
        user_request=mock_request,
        constraints="",
    )

    assert isinstance(result.response, SuggestedStudy)
    assert result.status.type == "success"
    assert result.status.code == 201
    assert "Study and website created successfully" in result.status.message
    assert len(result.to_save) == 2
    study_file = next((f for f in result.to_save if f.name == "suggested_study.json"), None)
    website_file = next((f for f in result.to_save if f.name == "study_website.html"), None)
    assert study_file is not None
    assert website_file is not None
    assert "<html" in website_file.content.lower()

@pytest.mark.asyncio
@pytest.mark.slow
async def test_create_diagram(config, suggested_study, event_bus):
    create_diagram_fn = create_diagram_function(config["llm_model"], event_bus)
    result = await create_diagram_fn(suggested_study=suggested_study)

    assert isinstance(result.response, str)
    assert "graph TD" in result.response
    assert len(result.to_save) == 1
    diagram_file = result.to_save[0]
    assert diagram_file.name == "study_with_diagram.json"
    assert diagram_file.model == "StudyWithDiagram"

@pytest.mark.asyncio
@pytest.mark.slow
async def test_create_summary_website(config, suggested_study, event_bus):
    create_summary_fn = create_summary_website_function(config["llm_model"], event_bus)
    
    # Create a study with diagram
    mock_diagram = StudyDiagram(
        diagram_code="""graph TD
        A[Start] --> B[Process]
        B --> C[Result]"""
    )
    mock_study_with_diagram = StudyWithDiagram(
        suggested_study=suggested_study,
        study_diagram=mock_diagram
    )
    
    result = await create_summary_fn(study_with_diagram=mock_study_with_diagram)
    
    assert isinstance(result.response, StudyWithDiagram)
    assert result.status.type == "success"
    assert result.status.code == 201
    assert "Summary website created successfully" in result.status.message
    assert len(result.to_save) == 1
    website_file = result.to_save[0]
    assert website_file.name == "study_website.html"
    assert "<html" in website_file.content.lower()
