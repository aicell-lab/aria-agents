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
from aria_agents.chatbot_extensions.study_suggester import SuggestedStudy
from aria_agents.utils import load_config

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
        description="A study investigating the effects of osmotic stress on yeast cell survival and function"
    )
