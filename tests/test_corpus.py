import pytest
from unittest.mock import patch
from aria_agents.chatbot_extensions.corpus import list_corpus, get_corpus, add_to_corpus
from aria_agents.utils import get_project_folder


@pytest.mark.asyncio
async def test_list_corpus_command():
    with patch(
        "aria_agents.chatbot_extensions.corpus.is_artifacts_available",
        return_value=True,
    ):
        result = await list_corpus()
        assert result.response == "/list_corpus"
        assert "Command to list corpus files sent" in result.status.message


@pytest.mark.asyncio
async def test_get_corpus_command():
    with patch(
        "aria_agents.chatbot_extensions.corpus.is_artifacts_available",
        return_value=True,
    ):
        result = await get_corpus(file_paths=["test.txt", "other.txt"])
        assert result.response == "/get_corpus test.txt,other.txt"
        assert "Command to get corpus files sent" in result.status.message


@pytest.mark.asyncio
async def test_add_to_corpus():
    with patch(
        "aria_agents.chatbot_extensions.corpus.is_artifacts_available",
        return_value=True,
    ):
        test_content = "Test file content"
        result = await add_to_corpus(
            file_name="test.txt", content=test_content, model=None
        )

        assert "Successfully added file" in result.response
        assert len(result.to_save) == 1
        assert result.to_save[0].name == "test.txt"
        assert result.to_save[0].content == test_content


@pytest.mark.asyncio
async def test_no_artifact_manager():
    with patch(
        "aria_agents.chatbot_extensions.corpus.is_artifacts_available",
        return_value=False,
    ):
        # Test list_corpus
        result = await list_corpus()
        assert result.status.type == "error"
        assert "No artifact manager available" in result.status.message

        # Test get_corpus
        result = await get_corpus(file_paths=["test.txt"])
        assert result.status.type == "error"
        assert "No artifact manager available" in result.status.message

        # Test add_to_corpus
        result = await add_to_corpus(file_name="test.txt", content="test")
        assert result.status.type == "error"
        assert "No artifact manager available" in result.status.message
