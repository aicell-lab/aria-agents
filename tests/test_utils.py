import pytest
import asyncio
from aria_agents.utils import call_agent, ask_agent, summary_website

@pytest.mark.asyncio
async def test_call_agent(artifact_manager, config):
    result = await call_agent(
        name="Test Agent",
        instructions="Test Instructions",
        messages=[],
        llm_model=config["llm_model"],
        artifact_manager=artifact_manager
    )
    assert result is not None
    assert "error" not in result

@pytest.mark.asyncio
async def test_ask_agent(artifact_manager, config):
    result = await ask_agent(
        name="Test Agent",
        instructions="Test Instructions",
        messages=[],
        output_schema=None,
        llm_model=config["llm_model"],
        artifact_manager=artifact_manager
    )
    assert result is not None
    assert "error" not in result

@pytest.mark.asyncio
async def test_summary_website(artifact_manager):
    content = "<html><body>Test Content</body></html>"
    filename = "test_summary.html"
    await summary_website(content, filename, artifact_manager)
    assert await artifact_manager.exists(filename)
