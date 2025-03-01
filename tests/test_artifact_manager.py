import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest
import httpx
from schema_agents.utils.common import EventBus
from hypha_rpc import connect_to_server
from tests.conftest import get_user_id, mock_http_get
from aria_agents.artifact_manager import AriaArtifacts

@pytest.fixture
def mock_server():
    server = MagicMock()
    server.config.public_base_url = "http://mockserver"
    artifact_service = MagicMock()
    artifact_service.create = AsyncMock()
    artifact_service.put_file = AsyncMock(return_value="http://mockserver/put_url")
    artifact_service.edit = AsyncMock()
    artifact_service.commit = AsyncMock()
    artifact_service.get_file = AsyncMock(return_value="http://mockserver/get_url")
    server.get_service = AsyncMock(return_value=artifact_service)
    return server

@pytest.fixture
def mock_event_bus():
    return MagicMock()

@pytest.fixture
def artifact_manager(mock_server, mock_event_bus):
    return AriaArtifacts(server=mock_server, event_bus=mock_event_bus)

@pytest.fixture(scope="session")
def event_bus():
    return EventBus(name="TestEventBus")

@pytest.fixture(scope="function")
async def hypha_artifact_manager(event_bus):
    server_url = "https://hypha.aicell.io"
    workspace_token = os.getenv("WORKSPACE_TOKEN")
    server = await connect_to_server(
        {
            "server_url": server_url,
            "token": workspace_token,
            "method_timeout": 500,
            "workspace": "aria-agents",
        }
    )
    art_man = AriaArtifacts(server, event_bus)

    user_token = os.getenv("TEST_HYPHA_TOKEN")
    user_id = get_user_id(user_token)
    session_id = "test-session-" + str(uuid.uuid4())
    await art_man.setup(
        token=user_token,
        user_id=user_id,
        session_id=session_id
    )
    return art_man

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
    mock_service = await mock_server.get_service()
    mock_service.create.assert_any_call(type='collection', workspace='ws-user-test_user', alias='aria-agents-chats', manifest=ANY)
    mock_service.create.assert_any_call(type='chat', parent_id='ws-user-test_user/aria-agents-chats', alias='aria-agents-chats:test_session', manifest=ANY)

@pytest.mark.asyncio
@patch("aria_agents.artifact_manager.get_server", new_callable=AsyncMock)
@patch("httpx.AsyncClient.put", new_callable=AsyncMock)
async def test_put_file(mock_http_put, mock_get_server, artifact_manager, mock_server):
    mock_get_server.return_value = mock_server
    mock_http_put.return_value = MagicMock(status_code=200)
    mock_event_bus = artifact_manager.get_event_bus()
    mock_event_bus.emit = MagicMock()

    await artifact_manager.setup(token="mock_token", user_id="test_user", session_id="test_session")
    await artifact_manager.put(value=b"test content", name="test_file.txt")

    mock_service = await mock_server.get_service()
    mock_service.edit.assert_called_once_with(artifact_id=artifact_manager._artifact_id, version="stage")
    mock_service.commit.assert_called_once_with(artifact_manager._artifact_id, version='new')
    mock_event_bus.emit.assert_called_once_with("store_put", "test_file.txt")

@pytest.mark.asyncio
@patch("aria_agents.artifact_manager.get_server", new_callable=AsyncMock)
@patch("httpx.AsyncClient.get", new_callable=lambda: AsyncMock(side_effect=mock_http_get))
async def test_get_file(httpx_get, mock_get_server, artifact_manager, mock_server):
    mock_get_server.return_value = mock_server

    await artifact_manager.setup(token="mock_token", user_id="test_user", session_id="test_session")
    content = await artifact_manager.get(name="test_file.txt")

    assert content == "file content"

@pytest.mark.asyncio
@patch("aria_agents.artifact_manager.get_server", new_callable=AsyncMock)
@patch("httpx.AsyncClient.put", new_callable=AsyncMock)
@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_event_bus_store_put(mock_http_get, mock_http_put, mock_get_server, artifact_manager, mock_server):
    mock_get_server.return_value = mock_server
    mock_http_put.return_value = MagicMock(status_code=200)
    mock_http_get.return_value = MagicMock(status_code=200, text="file content")
    mock_event_bus = artifact_manager.get_event_bus()
    mock_event_bus.emit = MagicMock()

    await artifact_manager.setup(token="mock_token", user_id="test_user", session_id="test_session")
    await artifact_manager.put(value=b"test content", name="test_file.txt")

    mock_event_bus.emit.assert_called_once_with("store_put", "test_file.txt")

    summary_website = await artifact_manager.get("test_file.txt")
    url = await artifact_manager.get_url("test_file.txt")

    assert summary_website == "file content"
    assert url == "http://mockserver/get_url"


@pytest.mark.asyncio
async def test_hypha_put_file(hypha_artifact_manager, event_bus):
    def assert_is_expected(name):
        assert name == "test_file.txt"

    event_bus.on("store_put", assert_is_expected)
    await hypha_artifact_manager.put(value=b"test content", name="test_file.txt")

    gotten_content = await hypha_artifact_manager.get("test_file.txt")
    url = await hypha_artifact_manager.get_url("test_file.txt")

    assert gotten_content == "test content"
    assert url.startswith("https://hypha.aicell.io/")
