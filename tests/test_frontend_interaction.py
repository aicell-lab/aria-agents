import pytest
from unittest.mock import patch
from aria_agents.chatbot_extensions.corpus import (
    get_corpus,
    list_corpus,
)

@pytest.mark.asyncio
async def test_frontend_corpus_commands():
    # Test list_corpus command
    with patch('aria_agents.chatbot_extensions.corpus.is_artifacts_available', return_value=True):
        result = await list_corpus()
        assert result.response == "/list_corpus"
        assert result.status.type == "success"

    # Test get_corpus command
    with patch('aria_agents.chatbot_extensions.corpus.is_artifacts_available', return_value=True):
        result = await get_corpus(file_paths=["test.txt"])
        assert result.response == "/get_corpus test.txt"
        assert result.status.type == "success"

@pytest.mark.asyncio 
async def test_frontend_availability_check():    
    # Test with is_artifacts_available mocked to False
    with patch('aria_agents.chatbot_extensions.corpus.is_artifacts_available', return_value=False):
        result = await list_corpus()
        assert result.status.type == "error"
        assert "No artifact manager available" in result.status.message
        
        result = await get_corpus(file_paths=["test.txt"])
        assert result.status.type == "error"
        assert "No artifact manager available" in result.status.message