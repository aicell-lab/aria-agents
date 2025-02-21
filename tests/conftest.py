import os
import pytest
import dotenv
from unittest.mock import AsyncMock, MagicMock
dotenv.load_dotenv()
from schema_agents.utils.common import EventBus
from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.utils import load_config
from aria_agents.server import get_server

@pytest.fixture(scope="session")
async def server():
    server_url = "https://hypha.aicell.io"
    workspace_name = os.environ.get("WORKSPACE_NAME", "aria-agents")
    token = os.getenv("WORKSPACE_TOKEN")
    return await get_server(server_url, workspace_name, token)

@pytest.fixture(scope="session")
async def artifact_manager(server):
    event_bus = EventBus(name="TestEventBus")
    art_man = AriaArtifacts(server, event_bus)
    await art_man.setup(
        token=os.getenv("WORKSPACE_TOKEN"),
        user_id="test-user",
        session_id="test-session"
    )
    return art_man

@pytest.fixture(scope="session")
def config():
    return load_config()


def attachment_format(filename, file_content):
    mock_file = MagicMock()
    mock_file.name = filename
    mock_file.content = file_content
    return mock_file

def get_file_in_folder(folder, format_func=None):
    this_path = os.path.dirname(os.path.dirname(__file__))
    folder_path = os.path.join(this_path, folder)
    def get_file(filename):
        path = os.path.join(folder_path, filename)
        with open(path, encoding="utf-8") as loaded_file:
            file_content = loaded_file.read()
            if format_func:
                return format_func(filename, file_content)
            return file_content
        
    return get_file

# TODO: mock_artifact_manager.put should save the file in a temporary directory
# TODO: exists should return True if the file is in the temporary directory
@pytest.fixture(scope="session")
def mock_artifact_manager():
    mock = MagicMock()
    mock.put = AsyncMock(return_value="mock_file_id")
    mock.get_url = AsyncMock(return_value="http://mock_url")
    mock.get = AsyncMock(side_effect=get_file_in_folder("tests/assets/studies"))
    mock.get_attachments = AsyncMock(return_value=[])
    mock.get_attachment = AsyncMock(side_effect=get_file_in_folder("tests/assets/attachments", format_func=attachment_format))
    mock.exists = AsyncMock(return_value=True)
    mock.get_event_bus = MagicMock(return_value=None)
    mock.user_id = "test-user"
    mock.session_id = "test-session"
    return mock