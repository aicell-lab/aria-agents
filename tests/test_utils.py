import pytest
from aria_agents.utils import call_agent, ask_agent
from aria_agents.chatbot_extensions.aux import write_website

@pytest.mark.asyncio
async def test_call_agent(config):
    result = await call_agent(
        name="Test Agent",
        instructions="Test Instructions",
        messages=[],
        llm_model=config["llm_model"],
        tools=[],
    )
    assert result is not None
    assert "error" not in result

@pytest.mark.asyncio
async def test_ask_agent(config):
    result = await ask_agent(
        name="Test Agent",
        instructions="Test Instructions",
        messages=[],
        output_schema=None,
        llm_model=config["llm_model"],
    )
    assert result is not None
    assert "error" not in result

@pytest.mark.asyncio
async def test_summary_website(mock_artifact_manager, suggested_study, config):
    website_type = "suggested_study"
    await write_website(suggested_study, mock_artifact_manager, website_type, llm_model=config["llm_model"])
    assert await mock_artifact_manager.exists(f"{website_type}.html")
