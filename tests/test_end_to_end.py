import pytest
import os
import uuid
from aria_agents.chatbot import connect_server

def status_callback(message):
    print(f"Message: {message}")

def artifact_callback(artifact, url):
    print(f"Artifact: {artifact}, URL: {url}")

@pytest.mark.asyncio
async def test_chat_end_to_end():
    rand_session_id = str(uuid.uuid4())
    service_id = "aria-agents-test"
    server = await connect_server("https://hypha.aicell.io", service_id)
    user_id = server.config.user["id"]
    service = await server.get_service(service_id)
    user_message = {
        "question": "I want to study the effect of osmotic stress on yeast cells. Suggest a study and make an experiment protocol",
        "chat_history": [],
        "chatbot_extensions": [{ id: "aria" }],
    }
    workspace_token = os.getenv("WORKSPACE_TOKEN")
    # constraints = "The only analytical equipment I have access to is an orbitrap mass spectrometer"
    await service.chat(
        text=user_message["question"],
        chat_history=user_message["chat_history"],
        status_callback=None,
        artifact_callback=None,
        session_id=rand_session_id,
        user_id=user_id,
        user_token=workspace_token,
        extensions=user_message["chatbot_extensions"],
    )
    assert "error" not in result["text"]
    assert result is not None
