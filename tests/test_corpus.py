import pytest
from schema_agents.utils.common import current_session
from aria_agents.chatbot_extensions.corpus import (
    create_list_corpus_function,
    create_get_corpus_function,
    create_add_to_corpus_function,
)
from aria_agents.utils import get_project_folder, get_session_id
import os

@pytest.mark.asyncio
async def test_list_corpus(config):
    list_corpus = create_list_corpus_function(config.get("event_bus"))
    result = await list_corpus()
    
    assert isinstance(result.response, str)
    assert "Successfully retrieved corpus file list" in result.response
    if "Found" in result.response:
        assert "Available files in corpus:" in result.response

@pytest.mark.asyncio
async def test_add_and_get_corpus(config):
    # First add a test file
    add_to_corpus = create_add_to_corpus_function(config.get("event_bus"))
    test_content = "Test file content"
    result = await add_to_corpus(
        file_name="test.txt",
        content=test_content
    )
    
    assert isinstance(result.response, str)
    assert "Successfully added file" in result.response
    assert len(result.to_save) == 1
    assert result.to_save[0].name == "test.txt"
    assert result.to_save[0].content == test_content
    
    # Then retrieve it
    get_corpus = create_get_corpus_function(config.get("event_bus"))
    result = await get_corpus(file_paths=["test.txt"])
    
    assert isinstance(result.response, str)
    assert "Retrieved 1 files successfully" in result.response
    assert test_content in result.response

@pytest.mark.asyncio
async def test_get_corpus_nonexistent(config):
    get_corpus = create_get_corpus_function(config.get("event_bus"))
    result = await get_corpus(file_paths=["nonexistent.txt"])
    
    assert isinstance(result.response, str)
    assert "Failed to retrieve" in result.response
    assert "Failed files:" in result.response
    assert "nonexistent.txt" in result.response