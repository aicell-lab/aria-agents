from unittest.mock import AsyncMock, MagicMock, patch, ANY
import pytest
from fastapi.testclient import TestClient
from packaging.version import Version
from fastapi import __version__ as fastapi_version
from aria_agents.chatbot import get_chatbot_api, serve_frontend

@pytest.fixture
def mock_server():
    server = MagicMock()
    server.register_service = AsyncMock()
    return server

@pytest.fixture
def test_client():
    app = get_chatbot_api("aria-agents-test")
    return TestClient(app)

@pytest.mark.asyncio
async def test_setup_service(mock_server):
    await serve_frontend(mock_server, "aria-agents-test")
    mock_server.register_service.assert_called_once_with(
        {
            "id": "aria-agents-test",
            "name": "Aria Agents UI",
            "type": "asgi",
            "serve": ANY,  # Complex callable, we just verify it exists
            "config": {"visibility": "public"},
        }
    )

@pytest.mark.skipif(Version(fastapi_version) < Version("0.115.0"), reason="This test requires a recent FastAPI version")
def test_chatbot_api_root(test_client):
    with patch("fastapi.responses.FileResponse") as mock_file_response:
        mock_file_response.return_value = "<html>Test</html>"
        response = test_client.get("/")
        assert response.status_code == 200

@pytest.mark.skipif(Version(fastapi_version) < Version("0.115.0"), reason="This test requires a recent FastAPI version")
def test_chatbot_api_static_files(test_client):
    static_routes = [
        route for route in test_client.app.routes if str(route.path).startswith("/js") or str(route.path).startswith("/css") or str(route.path).startswith("/img")
    ]
    assert len(static_routes) == 3, "Static files route should be mounted"
