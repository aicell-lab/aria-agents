import os
import pytest
import dotenv
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock
dotenv.load_dotenv()
from schema_agents.utils.common import EventBus
from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.utils import load_config
from aria_agents.server import get_server
from aria_agents.chatbot_extensions.study_suggester import SuggestedStudy


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

@pytest.fixture(scope="function")
def mock_artifact_manager():
    temp_dir = tempfile.mkdtemp()

    def put_file_in_temp_dir(filename, content):
        path = os.path.join(temp_dir, filename)
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(path, mode, encoding='utf-8' if mode == 'w' else None) as temp_file:
            temp_file.write(content)
        return path

    mock = MagicMock()
    mock.default_url = "http://mock_url"
    mock.put = AsyncMock(side_effect=lambda value, name: put_file_in_temp_dir(name, value))
    mock.get_url = AsyncMock(return_value=mock.default_url)
    mock.get = AsyncMock(side_effect=get_file_in_folder("tests/assets/studies"))
    mock.get_attachments = AsyncMock(return_value=[])
    mock.get_attachment = AsyncMock(side_effect=get_file_in_folder("tests/assets/attachments", format_func=attachment_format))
    mock.exists = AsyncMock(side_effect=lambda filename: os.path.exists(os.path.join(temp_dir, filename)))
    mock.get_event_bus = MagicMock(return_value=None)
    mock.user_id = "test-user"
    mock.session_id = "test-session"

    yield mock

    shutil.rmtree(temp_dir)

@pytest.fixture(scope="session")
def suggested_study():
    return SuggestedStudy(
        user_request="I want to study the effect of osmotic stress on yeast cells",
        experiment_name="Osmotic Stress on Yeast Cells",
        experiment_hypothesis="Osmotic stress affects yeast cells",
        experiment_expected_results="Yeast cells will die under osmotic stress",
        experiment_material=["Yeast cells", "Osmotic stress solution"],
        experiment_reasoning="Osmotic stress is known to affect cells",
        experiment_workflow="Expose yeast cells to osmotic stress and observe results",
        references=["https://www.ncbi.nlm.nih.gov/pubmed/12345678"],
    )
