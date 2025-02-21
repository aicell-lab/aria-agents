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
async def test_summary_website(artifact_manager):
    content = "<html><body>Test Content</body></html>"
    filename = "test_summary.html"
    await write_website(content, filename, artifact_manager)
    assert await artifact_manager.exists(filename)
