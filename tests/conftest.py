import pytest
import os
import dotenv
dotenv.load_dotenv()
from schema_agents.utils.common import EventBus
from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.utils import load_config
from aria_agents.server import get_server

@pytest_asyncio.fixture(scope="session")
async def server():
    server_url = "https://hypha.aicell.io"
    workspace_name = os.environ.get("WORKSPACE_NAME", "aria-agents")
    token = os.getenv("WORKSPACE_TOKEN")
    return await get_server(server_url, workspace_name, token)

@pytest_asyncio.fixture
async def artifact_manager(server):
    event_bus = EventBus(name="TestEventBus")
    artifact_manager = AriaArtifacts(server, event_bus)
    await artifact_manager.setup(
        token=os.getenv("WORKSPACE_TOKEN"),
        user_id="test-user",
        session_id="test-session"
    )
    return artifact_manager

@pytest.fixture
def config():
    return load_config()
