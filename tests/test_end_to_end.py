import pytest
import os
import uuid
from aria_agents.chatbot import register_chat_service
from tests.conftest import get_user_id

accumulated_args = []

def status_callback(message):
    accumulated_args.append(message.arguments)

def artifact_callback(content, url):
    assert url.startswith("http")
    assert content.startswith("<!DOCTYPE html>")

@pytest.mark.asyncio
async def test_chat_end_to_end(server_promise, chat_input):
    rand_session_id = str(uuid.uuid4())
    service_id = "aria-agents-test"
    server = await server_promise
    user_token = os.getenv("TEST_HYPHA_TOKEN")
    user_id = get_user_id(user_token)
    await register_chat_service(server, service_id)
    service = await server.get_service(service_id)
    await service.chat(
        text=chat_input["question"],
        chat_history=chat_input["chat_history"],
        status_callback=status_callback,
        artifact_callback=artifact_callback,
        session_id=rand_session_id,
        user_id=user_id,
        user_token=user_token,
        extensions=chat_input["chatbot_extensions"],
    )
    full_output = "".join(accumulated_args)
    assert "error" not in full_output

