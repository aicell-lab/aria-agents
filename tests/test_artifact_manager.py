import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.server import get_server

@pytest.fixture
def mock_server():
    server = MagicMock()
    server.config.public_base_url = "http://mockserver"
    server.get_service = AsyncMock(return_value=MagicMock())
    server.create = AsyncMock()
    server.put_file = AsyncMock()
    server.edit = AsyncMock()
    server.commit = AsyncMock()
    server.get_file = AsyncMock()
    return server

@pytest.fixture
def mock_event_bus():
    return MagicMock()

@pytest.fixture
def artifact_manager(mock_server, mock_event_bus):
    return AriaArtifacts(server=mock_server, event_bus=mock_event_bus)

@pytest.mark.asyncio
@patch("aria_agents.artifact_manager.get_server", new_callable=AsyncMock)
async def test_setup(mock_get_server, artifact_manager, mock_server):
    mock_get_server.return_value = mock_server
    await artifact_manager.setup(token="mock_token", user_id="test_user", session_id="test_session")
    assert artifact_manager.user_id == "test_user"
    assert artifact_manager.session_id == "test_session"
    assert artifact_manager._workspace == "ws-user-test_user"
    assert artifact_manager._collection_alias == "aria-agents-chats"
    assert artifact_manager._collection_id == "ws-user-test_user/aria-agents-chats"
    assert artifact_manager._artifact_id == "ws-user-test_user/aria-agents-chats:test_session"

@pytest.mark.asyncio
async def test_create_artifact(artifact_manager, mock_server):
    mock_server.get_service().create_artifact = AsyncMock(return_value="artifact_id")
    artifact_id = await artifact_manager.create_artifact(name="test_artifact")
    assert artifact_id == "artifact_id"
    mock_server.get_service().create_artifact.assert_called_once_with(name="test_artifact")

@pytest.mark.asyncio
async def test_put_file(artifact_manager, mock_server):
    mock_server.get_service().put_file = AsyncMock(return_value="http://mockserver/put_url")
    mock_server.get_service().edit = AsyncMock()
    mock_server.get_service().commit = AsyncMock()
    mock_event_bus = artifact_manager.get_event_bus()
    mock_event_bus.emit = MagicMock()

    await artifact_manager.setup(token="mock_token", user_id="test_user", session_id="test_session")
    await artifact_manager.put(value=b"test content", name="test_file.txt")

    mock_server.get_service().edit.assert_called_once_with(artifact_id=artifact_manager._artifact_id, version="stage")
    mock_server.get_service().commit.assert_called_once_with(artifact_manager._artifact_id)
    mock_event_bus.emit.assert_called_once_with("store_put", "test_file.txt")

@pytest.mark.asyncio
async def test_get_file(artifact_manager, mock_server):
    mock_server.get_service().get_file = AsyncMock(return_value="http://mockserver/get_url")
    async def mock_http_get(url, timeout):
        class MockResponse:
            def raise_for_status(self):
                pass
            @property
            def text(self):
                return "file content"
        return MockResponse()
    httpx.AsyncClient.get = mock_http_get

    await artifact_manager.setup(token="mock_token", user_id="test_user", session_id="test_session")
    content = await artifact_manager.get(name="test_file.txt")

    assert content == "file content"

@pytest.mark.asyncio
async def test_event_bus_store_put(artifact_manager, mock_server):
    mock_server.get_service().put_file = AsyncMock(return_value="http://mockserver/put_url")
    mock_server.get_service().edit = AsyncMock()
    mock_server.get_service().commit = AsyncMock()
    mock_event_bus = artifact_manager.get_event_bus()
    mock_event_bus.emit = MagicMock()

    await artifact_manager.setup(token="mock_token", user_id="test_user", session_id="test_session")
    await artifact_manager.put(value=b"test content", name="test_file.txt")

    mock_event_bus.emit.assert_called_once_with("store_put", "test_file.txt")

    summary_website = await artifact_manager.get("test_file.txt")
    url = await artifact_manager.get_url("test_file.txt")

    assert summary_website == "file content"
    assert url == "http://mockserver/get_url"
