import pytest
import os
import uuid
from hypha_rpc import connect_to_server
from hypha_rpc.rpc import RemoteException
from aria_agents.chatbot import register_chat_service
from tests.conftest import get_user_id

output_messages = []

def status_callback(message):
    match message.status:
        case "start":
            output_messages.append(message.arguments)
        case "in_progress":
            output_messages[-1] += message.arguments
        case "finished":
            output_messages[-1] += message.arguments
            print("FULL_OUTPUT_MESSAGE:", output_messages[-1])
            assert "error" not in output_messages[-1].lower(), f"Error in chatbot: {output_messages[-1]}"

def artifact_callback(content, url):
    assert url.startswith("http")
    assert content.startswith("<!DOCTYPE html>")

@pytest.mark.asyncio
async def test_chat_end_to_end(chat_input):
    rand_session_id = str(uuid.uuid4())
    service_id = "aria-agents-test"
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
    user_token = os.getenv("TEST_HYPHA_TOKEN")
    user_id = get_user_id(user_token)
    await register_chat_service(server, service_id)
    service = await server.get_service(service_id)
    try:
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
    except RemoteException as e:
        if "Session stopped" not in str(e):
            raise e
