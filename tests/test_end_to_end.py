import pytest
from aria_agents.chatbot import chat

@pytest.mark.asyncio
async def test_chat_end_to_end(artifact_manager, config):
    user_message = {
        "question": "I want to study the effect of osmotic stress on yeast cells",
        "chat_history": [],
        "chatbot_extensions": [],
        "context": {}
    }
    # constraints = "The only analytical equipment I have access to is an orbitrap mass spectrometer"
    result = await chat(
        text=user_message["question"],
        chat_history=user_message["chat_history"],
        status_callback=lambda x: None,
        artifact_callback=lambda x, y: None,
        session_id="test-session",
        user_id="test-user",
        user_token=os.getenv("WORKSPACE_TOKEN"),
        extensions=user_message["chatbot_extensions"],
        assistant_name="Aria",
        context=user_message["context"]
    )
    assert "error" not in result["text"]
    assert result is not None
