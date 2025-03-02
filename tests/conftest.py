import os
import base64
import json
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock
import pytest
import dotenv
dotenv.load_dotenv()
from schema_agents.utils.common import EventBus
from aria_agents.utils import load_config, create_query_function
from aria_agents.chatbot_extensions.study_suggester import SuggestedStudy

@pytest.fixture
def output_handler():
    class OutputMessageHandler:
        def __init__(self):
            self.output_messages = [""]

        def status_callback(self, message):
            self.output_messages[-1] += message["arguments"]
            if message["status"] == "finished":
                assert "error" not in self.output_messages[-1].lower(), f"Chatbot mentioned error: {self.output_messages[-1]}"
                self.output_messages.append("")

    return OutputMessageHandler()

@pytest.fixture
def event_bus(output_handler):
    return_event_bus = EventBus(name="TestEventBus")
    return_event_bus.on("stream", lambda message: output_handler.status_callback(message.model_dump()))
    return return_event_bus

def mock_get_query_function(query_index_dir=None, config=None):
    mock_response = MagicMock()
    mock_response.response = "This is a mock response for the query."
    class Node:
        def __init__(self, num):
            self.num = num
        @property
        def metadata(self):
            return {"URL": f"http://example.com/article{self.num}"}
    mock_response.source_nodes = [
        Node(1),
        Node(2),
    ]
    mock_query_engine = MagicMock()
    mock_query_engine.query = MagicMock(return_value=mock_response)
    return create_query_function(mock_query_engine)

async def mock_http_get(url, *args, **kwargs):
    class MockResponse:
        def raise_for_status(self):
            pass
        @property
        def text(self):
            return "file content"
        @property
        def content(self):
            return b"<test>file content</test>"
    return MockResponse()

@pytest.fixture(scope="session")
def chat_input():
    return {
        "question": "I want to study the effect of osmotic stress on yeast cells. Suggest a study and make an experiment protocol",
        "chat_history": [],
        "chatbot_extensions": [{ "id": "aria" }],
        "constraints": "I only have access to a microscope and a centrifuge",
    }

def get_user_id(user_token):
    payload = user_token.split('.')[1]
    padded_payload = payload + '=' * (-len(payload) % 4)  # Add padding if necessary
    decoded_payload = base64.urlsafe_b64decode(padded_payload)
    user_info = json.loads(decoded_payload)
    return user_info['sub']

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
def mock_artifact_manager(event_bus):
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
    mock.get_event_bus = MagicMock(return_value=event_bus)
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
