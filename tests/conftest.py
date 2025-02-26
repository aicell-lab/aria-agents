import os
import tempfile
import uuid
import shutil
from unittest.mock import AsyncMock, MagicMock
import pytest
import dotenv
from hypha_rpc import connect_to_server
dotenv.load_dotenv()
from schema_agents.utils.common import EventBus
from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.utils import load_config
from aria_agents.chatbot_extensions.study_suggester import SuggestedStudy
import base64
import json


@pytest.fixture(scope="session")
def chat_input():
    return {
        "question": "I want to study the effect of osmotic stress on yeast cells. Suggest a study and make an experiment protocol",
        "chat_history": [],
        "chatbot_extensions": [{ "id": "aria" }],
        "constraints": "I only have access to a microscope and a centrifuge",
    }

@pytest.fixture(scope="session")
def server_promise():
    server_url = "https://hypha.aicell.io"
    token = os.getenv("WORKSPACE_TOKEN")
    return connect_to_server(
        {
            "server_url": server_url,
            "token": token,
            "method_timeout": 500,
            "workspace": "aria-agents",
        }
    )

@pytest.fixture(scope="session")
async def static_server(server_promise):
    async with await server_promise as server:
        yield server

def get_user_id(user_token):
    payload = user_token.split('.')[1]
    padded_payload = payload + '=' * (-len(payload) % 4)  # Add padding if necessary
    decoded_payload = base64.urlsafe_b64decode(padded_payload)
    user_info = json.loads(decoded_payload)
    return user_info['sub']

@pytest.fixture(scope="function")
async def artifact_manager(server_promise):
    event_bus = EventBus(name="TestEventBus")
    server = await server_promise
    user_id = get_user_id(server)
    art_man = AriaArtifacts(server, event_bus)
    session_id = str(uuid.uuid4())
    await art_man.setup(
        token=os.getenv("TEST_HYPHA_TOKEN"),
        user_id=user_id,
        session_id=session_id
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
