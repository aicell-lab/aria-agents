import dotenv

dotenv.load_dotenv()
import asyncio
import datetime
import json
import logging
import os
import re
import secrets
from typing import Any, Dict, List, Optional

import aiofiles
import pkg_resources
from hypha_rpc import connect_to_server, login
from pydantic import BaseModel, Field
from schema_agents import Message, Role
from schema_agents.utils.common import EventBus

from aria_agents.chatbot_extensions import (
    convert_to_dict,
    create_tool_name,
    extension_to_tools,
    get_builtin_extensions,
)
from aria_agents.hypha_store import HyphaDataStore
from aria_agents.quota import QuotaManager
from aria_agents.utils import (
    ChatbotExtension,
    LegacyChatbotExtension,
    legacy_extension_to_tool,
)

logger = logging.getLogger("bioimageio-chatbot")
# set logger level
logger.setLevel(logging.INFO)


# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "chatbot_extensions", "config.json")
with open(config_file, "r") as file:
    CONFIG = json.load(file)


class UserProfile(BaseModel):
    """The user's profile. This will be used to personalize the response to the user."""

    name: str = Field(description="The user's name.", max_length=32)
    occupation: str = Field(description="The user's occupation.", max_length=128)
    background: str = Field(description="The user's background.", max_length=256)


class QuestionWithHistory(BaseModel):
    """The user's question, chat history, and user's profile."""

    question: str = Field(description="The user's question.")
    chat_history: Optional[List[Dict[str, str]]] = Field(
        None, description="The chat history."
    )
    user_profile: Optional[UserProfile] = Field(
        None,
        description="The user's profile. You should use this to personalize the response based on the user's background and occupation.",
    )
    chatbot_extensions: Optional[List[Dict[str, Any]]] = Field(
        None, description="Chatbot extensions."
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="The context of request."
    )


class ResponseStep(BaseModel):
    """Response step"""

    name: str = Field(description="Step name")
    details: Optional[dict] = Field(None, description="Step details")


class RichResponse(BaseModel):
    """Rich response with text and intermediate steps"""

    text: str = Field(description="Response text")
    steps: List[ResponseStep] = Field(description="Intermediate steps")
    remaining_quota: Optional[float] = Field(None, description="Remaining quota")


def create_assistants(builtin_extensions, event_bus: EventBus):
    # debug = os.environ.get("BIOIMAGEIO_DEBUG") == "true"

    async def respond_to_user(
        question_with_history: QuestionWithHistory = None, role: Role = None
    ) -> RichResponse:
        """Response to the user's query."""
        steps = []
        inputs = (
            [question_with_history.user_profile]
            + list(question_with_history.chat_history)
            + [question_with_history.question]
        )
        assert question_with_history.chatbot_extensions is not None
        extensions_by_id = {ext.id: ext for ext in builtin_extensions}
        extensions_by_name = {ext.name: ext for ext in builtin_extensions}
        extensions_by_tool_name = {}

        tools = []
        tool_prompts = {}
        for ext in question_with_history.chatbot_extensions:
            if "id" in ext and ext["id"] in extensions_by_id:
                extension = extensions_by_id[ext["id"]]
            elif "name" in ext and ext["name"] in extensions_by_name:
                extension = extensions_by_name[ext["name"]]
            else:
                if "tools" not in ext and "execute" in ext and "get_schema" in ext:
                    # legacy chatbot extension
                    extension = LegacyChatbotExtension.model_validate(ext)
                    logger.warning(
                        f"Legacy chatbot extension is deprecated. Please use the new ChatbotExtension interface for {extension.name} with multi-tool support."
                    )
                else:
                    extension = ChatbotExtension.model_validate(ext)

            max_length = 4000
            if isinstance(extension, LegacyChatbotExtension):
                ts = [await legacy_extension_to_tool(extension)]
                assert (
                    len(extension.description) <= max_length
                ), f"Extension description is too long: {extension.description}"
                tool_prompts[create_tool_name(extension.name)] = (
                    extension.description.replace("\n", ";")[:max_length]
                )
            else:
                ts = await extension_to_tools(extension)
                assert (
                    len(extension.description) <= max_length
                ), f"Extension tool prompt is too long: {extension.description}"
                tool_prompts[create_tool_name(extension.id) + "*"] = (
                    extension.description.replace("\n", ";")[:max_length]
                )
            extensions_by_tool_name.update({t.__name__: extension for t in ts})
            tools += ts

        class ThoughtsSchema(BaseModel):
            """Details about the thoughts"""

            reasoning: str = Field(
                ...,
                description="reasoning and constructive self-criticism; make it short and concise in less than 20 words",
            )
            # reasoning: str = Field(..., description="brief explanation about the reasoning")
            # criticism: str = Field(..., description="constructive self-criticism")

        tool_usage_prompt = (
            "Tool usage guidelines (* represent the prefix of a tool group):\n"
            + "\n".join(
                [f" - {ext}:{tool_prompt}" for ext, tool_prompt in tool_prompts.items()]
            )
        )
        response, metadata = await role.acall(
            inputs,
            tools,
            return_metadata=True,
            thoughts_schema=ThoughtsSchema,
            max_loop_count=20,
            tool_usage_prompt=tool_usage_prompt,
        )
        result_steps = metadata["steps"]
        for idx, step_list in enumerate(result_steps):
            steps.append(
                ResponseStep(
                    name=f"step-{idx}", details={"details": convert_to_dict(step_list)}
                )
            )
        return RichResponse(text=response, steps=steps)

    aria_instructions = (
        "As Aria, your role is to serve as an assistant in autonomous scientific discovery. "
        "Your primary focus is on addressing inquiries related to various scientific tasks, ensuring your responses are accurate, concise, logical, educational, and engaging. "
        "Your mission is to decipher the user's needs through clarifying questions and assist them by invoking the provided tools available in the Aria Agents repository. "
        "These tools are designed to aid in various scientific tasks and may include functionalities such as data retrieval, analysis, visualization, and more. "
        "You'll be leveraging your knowledge and the tools available to facilitate scientific exploration and discovery. "
        "Your interactions should foster a collaborative and productive environment for scientific inquiry within the Aria Agents community."
    )

    aria = Role(
        name="Aria",
        instructions=aria_instructions,
        icon="./img/favicon-32x32.png",
        actions=[respond_to_user],
        event_bus=event_bus,
        register_default_events=True,
        model=CONFIG["llm_model"],
    )

    # convert to a list
    all_extensions = [
        {"id": ext.id, "name": ext.name, "description": ext.description}
        for ext in builtin_extensions
    ]

    return [
        {
            "name": "Aria",
            "agent": aria,
            "extensions": all_extensions,
            "code_interpreter": False,
            "alias": "Aria",
            "icon": "https://bioimage.io/static/img/bioimage-io-icon.svg",
            "welcome_message": "Hi there! I'm Aria. How can I help you today?",
        },
    ]


async def save_chat_history(chat_log_full_path, chat_his_dict):
    # Serialize the chat history to a json string
    chat_history_json = json.dumps(chat_his_dict)

    # Write the serialized chat history to the json file
    async with aiofiles.open(chat_log_full_path, mode="w", encoding="utf-8") as f:
        await f.write(chat_history_json)


async def connect_server(server_url, client_id):
    """Connect to the server and register the chat service."""
    login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    provided_token = os.environ.get("HYPHA_ADMIN_TOKEN")
    workspace_name = os.environ.get("WORKSPACE_NAME", "aria-agents")
    
    if login_required:
        if provided_token is None:
            token = await login({"server_url": server_url})
        else:
            token = provided_token
    else:
        token = None
    server = await connect_to_server(
        {"server_url": server_url, "token": token, "client_id": client_id, "method_timeout": 500, "workspace": workspace_name}
    )
    await register_chat_service(server)


async def register_chat_service(server):
    """Hypha startup function."""
    debug = os.environ.get("BIOIMAGEIO_DEBUG") == "true"
    event_bus = EventBus(name="AriaAgents")
    data_store = HyphaDataStore(event_bus)
    await data_store.setup(server)
    builtin_extensions = get_builtin_extensions(data_store)
    login_required = os.environ.get("BIOIMAGEIO_LOGIN_REQUIRED") == "true"
    chat_logs_path = os.environ.get("BIOIMAGEIO_CHAT_LOGS_PATH", "./chat_logs")
    default_quota = float(os.environ.get("BIOIMAGEIO_DEFAULT_QUOTA", "inf"))
    reset_period = os.environ.get("BIOIMAGEIO_DEFAULT_RESET_PERIOD", "hourly")
    quota_database_path = os.environ.get("BIOIMAGEIO_QUOTA_DATABASE_PATH", ":memory:")
    quota_manager = QuotaManager(
        db_file=quota_database_path,
        vip_list=[],
        default_quota=default_quota,
        default_reset_period=reset_period,
    )
    assert (
        chat_logs_path is not None
    ), "Please set the BIOIMAGEIO_CHAT_LOGS_PATH environment variable to the path of the chat logs folder."
    if not os.path.exists(chat_logs_path):
        print(
            f"The chat session folder is not found at {chat_logs_path}, will create one now."
        )
        os.makedirs(chat_logs_path, exist_ok=True)

    assistants = create_assistants(builtin_extensions, event_bus)

    def load_authorized_emails():
        if login_required:
            authorized_users_path = os.environ.get("BIOIMAGEIO_AUTHORIZED_USERS_PATH")
            if authorized_users_path:
                assert os.path.exists(
                    authorized_users_path
                ), f"The authorized users file is not found at {authorized_users_path}"
                with open(authorized_users_path, "r") as f:
                    authorized_users = json.load(f)["users"]
                authorized_emails = [
                    user["email"] for user in authorized_users if "email" in user
                ]
            else:
                authorized_emails = None
        else:
            authorized_emails = None
        return authorized_emails

    authorized_emails = load_authorized_emails()

    def check_permission(user):
        if user["is_anonymous"]:
            return False
        if authorized_emails is None or user["email"] in authorized_emails:
            return True
        else:
            return False

    async def report(user_report, context=None):
        if login_required and context and context.get("user"):
            assert check_permission(
                context.get("user")
            ), "You don't have permission to report the chat history."
        # get the chatbot version
        version = pkg_resources.get_distribution("aria_agents").version
        chat_his_dict = {
            "type": user_report["type"],
            "feedback": user_report["feedback"],
            "conversations": user_report["messages"],
            "session_id": user_report["session_id"],
            "timestamp": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "user": context.get("user"),
            "version": version,
        }
        session_id = user_report["session_id"] + secrets.token_hex(4)
        filename = f"report-{session_id}.json"
        # Create a chat_log.json file inside the session folder
        chat_log_full_path = os.path.join(chat_logs_path, filename)
        await save_chat_history(chat_log_full_path, chat_his_dict)
        print(f"User report saved to {filename}")

    async def talk_to_assistant(
        assistant_name,
        session_id,
        user_message: QuestionWithHistory,
        status_callback,
        artefact_callback,
        finished_callback,
        user,
        cross_assistant=False,
    ):
        user = user or {}
        if quota_manager.check_quota(user.get("email")) <= 0:
            raise PermissionError(
                "You have exceeded the quota limit. Please wait for the quota to reset."
            )

        assistant_names = [a["name"] for a in assistants]
        assert (
            assistant_name in assistant_names
        ), f"Assistant {assistant_name} is not found."
        # find assistant by name
        assistant = next(a["agent"] for a in assistants if a["name"] == assistant_name)
        session_id = session_id or secrets.token_hex(8)

        # Listen to the `stream` event
        async def stream_callback(message):
            if message.type in ["function_call", "text"]:
                if message.session.id == session_id:
                    await status_callback(message.model_dump())

        event_bus.on("stream", stream_callback)

        # Listen to the `store_put` event
        async def store_put_callback(store_obj):
            if store_obj["type"] == "file" and store_obj["name"].endswith(".html"):
                summary_website = store_obj["value"]
                url = data_store.get_url(store_obj["id"])
                await artefact_callback(summary_website, url)

        event_bus.on("store_put", store_put_callback)

        try:
            response = await assistant.handle(
                Message(
                    content="", data=user_message, role="User", session_id=session_id
                )
            )
        except Exception as e:
            event_bus.off("stream", stream_callback)
            event_bus.off("store_put", store_put_callback)
            raise e

        quota_manager.use_quota(user.get("email"), 1.0)
        event_bus.off("stream", stream_callback)
        event_bus.off("store_put", store_put_callback)
        # get the content of the last response
        response = response[-1].data  # type: RichResponse
        assert isinstance(response, RichResponse)
        response.remaining_quota = quota_manager.check_quota(user.get("email"))
        print(
            f"\nUser: {user_message.question}\nAssistant({assistant_name}): {response.text}\nRemaining quota: {response.remaining_quota}\n"
        )
        if cross_assistant:
            response.text = f"`{assistant_name}`: {response.text}"

        if session_id:
            user_message.chat_history.append(
                {"role": "user", "content": user_message.question}
            )
            user_message.chat_history.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "steps": [step.dict() for step in response.steps],
                }
            )
            version = pkg_resources.get_distribution("aria_agents").version
            chat_his_dict = {
                "conversations": user_message.chat_history,
                "timestamp": str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "user": user_message.context.get("user"),
                "assistant_name": assistant_name,
                "version": version,
            }
            filename = f"chatlogs-{session_id}.json"
            chat_log_full_path = os.path.join(chat_logs_path, filename)
            await save_chat_history(chat_log_full_path, chat_his_dict)
            print(f"Chat history saved to {filename}")
            await finished_callback()
        return response.model_dump()

    async def chat(
        text,
        chat_history,
        user_profile=None,
        status_callback=None,
        artefact_callback=None,
        finished_callback=None,
        session_id=None,
        extensions=None,
        assistant_name="Aria",
        context=None,
    ):
        if login_required and context and context.get("user"):
            logger.info(f"User: {context.get('user')}, Message: {text}")
            assert check_permission(
                context.get("user")
            ), "You don't have permission to use the chatbot, please sign up and wait for approval"

        text = text.strip()

        assistant_names = [a["name"].lower() for a in assistants]

        # Check if the text starts with @ followed by a name
        match = re.match(r"@(\w+)", text, flags=re.IGNORECASE)
        if match:
            # If it does, extract the name and set it as the assistant_name
            assistant_name = match.group(1).lower()
            # Check if the assistant_name is in the list of assistant_names
            if assistant_name not in assistant_names:
                raise ValueError(
                    f"Assistant '{assistant_name}' not found. Available assistants are {assistant_names}"
                )
            # Remove the @name part from the text
            text = re.sub(r"@(\w+)", "", text, 1).strip()
            assistant_name = assistants[assistant_names.index(assistant_name)]["name"]
            cross_assistant = True
        else:
            cross_assistant = False

        m = QuestionWithHistory(
            question=text,
            chat_history=chat_history,
            user_profile=UserProfile.model_validate(user_profile),
            chatbot_extensions=extensions,
            context=context,
        )

        return await talk_to_assistant(
            assistant_name,
            session_id,
            m,
            status_callback,
            artefact_callback,
            finished_callback,
            context.get("user"),
            cross_assistant,
        )

    async def ping(context=None):
        if login_required and context and context.get("user"):
            assert check_permission(
                context.get("user")
            ), "You don't have permission to use the chatbot, please sign up and wait for approval"
        return "pong"

    assistant_keys = [
        "name",
        "extensions",
        "alias",
        "icon",
        "welcome_message",
        "code_interpreter",
    ]
    version = pkg_resources.get_distribution("aria_agents").version
    hypha_service_info = await server.register_service(
        {
            "name": "Aria Agents",
            "id": "aria-agents",
            "config": {"visibility": "public", "require_context": True},
            "version": version,
            "ping": ping,
            "chat": chat,
            "report": report,
            "assistants": {
                a["name"]: {k: a[k] for k in assistant_keys} for a in assistants
            },
        }
    )

    server_info = await server.get_connection_info()

    server_url = server.config["public_base_url"]

    service_id = hypha_service_info["id"]
    print("=============================\n")
    if server_url.startswith("http://localhost") or server_url.startswith(
        "http://127.0.0.1"
    ):
        print(f"To test the Aria Assistant locally, visit: {server_url}/chat")
    print(
        # f"\nThe chat client are available publicly at: https://bioimage.io/chat?server={server_url}&service_id={service_id}\n"
        "\n=============================\n"
    )


if __name__ == "__main__":
    server_url = """https://ai.imjoy.io"""
    loop = asyncio.get_event_loop()
    loop.create_task(connect_server(server_url, "aria_agents_test_client"))
    loop.run_forever()
