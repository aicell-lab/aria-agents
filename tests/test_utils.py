import pytest
from aria_agents.utils import call_agent, ask_agent
from aria_agents.chatbot_extensions.aux import write_website

@pytest.mark.slow
@pytest.mark.asyncio
async def test_call_agent(config):
    result = await call_agent(
        name="Test Agent",
        instructions="Test Instructions",
        messages=[],
        llm_model=config["llm_model"],
        tools=[],
        event_bus=config.get("event_bus"),
    )
    assert result is not None
    assert isinstance(result, str)
    assert "error" not in result.lower()

@pytest.mark.slow
@pytest.mark.asyncio
async def test_ask_agent(config):
    result = await ask_agent(
        name="Test Agent",
        instructions="Test Instructions",
        messages=[],
        output_schema=None,
        llm_model=config["llm_model"],
        event_bus=config.get("event_bus"),
    )
    assert result is not None
    assert isinstance(result, str)
    assert "error" not in result.lower()

@pytest.mark.slow
@pytest.mark.asyncio
async def test_summary_website(suggested_study, config):
    website_type = "suggested_study"
    website_content = await write_website(
        suggested_study, 
        config.get("event_bus"),
        website_type, 
        llm_model=config["llm_model"]
    )
    assert isinstance(website_content, str)
    assert len(website_content) > 0
    assert "<html" in website_content.lower()
