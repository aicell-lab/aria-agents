import os
import uuid
import json
from typing import Any, Callable, Dict, Optional, _UnionGenericAlias
from inspect import signature
from contextvars import ContextVar
import dotenv
from pydantic import BaseModel, Field
from schema_agents.utils.common import current_session
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from aria_agents.jsonschema_pydantic import json_schema_to_pydantic_model
from aria_agents.artifact_manager import AriaArtifacts


async def call_agent(
    name,
    instructions,
    messages,
    llm_model,
    event_bus=None,
    constraints=None,
    tools=None,
    output_schema=None,
):
    session_id = get_session_id(current_session)
    agent = Role(
        name=name,
        instructions=instructions,
        icon="🤖",
        constraints=constraints,
        event_bus=event_bus,
        register_default_events=True,
        model=llm_model,
    )

    async with create_session_context(id=session_id, role_setting=agent.role_setting):
        return await agent.acall(messages, tools=tools, output_schema=output_schema)


async def ask_agent(
    name,
    instructions,
    messages,
    output_schema,
    llm_model,
    event_bus=None,
    constraints=None,
):
    agent = Role(
        name=name,
        instructions=instructions,
        icon="🤖",
        constraints=constraints,
        event_bus=event_bus,
        register_default_events=True,
        model=llm_model,
    )
    session_id = get_session_id(current_session)
    async with create_session_context(id=session_id, role_setting=agent.role_setting):
        return await agent.aask(
            messages,
            output_schema=output_schema,
        )


def save_locally(filename: str, content: str, project_folder: str):
    file_path = os.path.join(project_folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return "file://" + file_path


async def save_to_artifact_manager(
    filename: str, content: str, artifact_manager: AriaArtifacts
):
    file_id = await artifact_manager.put(
        value=content,
        name=filename,
    )
    file_url = await artifact_manager.get_url(name=file_id)
    return file_url


async def get_file(filename: str, artifact_manager: AriaArtifacts = None):
    if artifact_manager is None:
        session_id = get_session_id(current_session)
        project_folder = get_project_folder(session_id)
        file_content = os.path.join(project_folder, filename)
        with open(file_content, encoding="utf-8") as loaded_file:
            return json.load(loaded_file)
    else:
        file_content = await artifact_manager.get(filename)
        return json.loads(file_content)


async def save_file(
    filename: str, content: str, artifact_manager: AriaArtifacts = None
):
    if artifact_manager is None:
        session_id = get_session_id(current_session)
        project_folder = get_project_folder(session_id)
        file_url = save_locally(filename, content, project_folder)
    else:
        file_url = await save_to_artifact_manager(filename, content, artifact_manager)

    return file_url


def load_config():
    this_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(this_dir, "chatbot_extensions/config.json")
    with open(config_file, "r", encoding="utf-8") as file:
        config = json.load(file)
    return config


def extract_schemas(function):
    sig = signature(function)
    positional_annotation = [
        p.annotation
        for p in sig.parameters.values()
        if p.kind == p.POSITIONAL_OR_KEYWORD
    ][0]
    output_schemas = (
        [sig.return_annotation]
        if not isinstance(sig.return_annotation, _UnionGenericAlias)
        else list(sig.return_annotation.__args__)
    )
    input_schemas = (
        [positional_annotation]
        if not isinstance(positional_annotation, _UnionGenericAlias)
        else list(positional_annotation.__args__)
    )
    return input_schemas, output_schemas


class ChatbotExtension(BaseModel):
    """Chatbot extension."""

    id: str
    name: str
    description: str
    tools: Optional[Dict[str, Any]] = {}
    get_schema: Optional[Callable] = None


class LegacyChatbotExtension(BaseModel):
    """A class that defines the interface for a user extension"""

    name: str = Field(..., description="The name of the extension")
    description: str = Field(..., description="A description of the extension")
    get_schema: Optional[Callable] = Field(
        None, description="A function that returns the schema for the extension"
    )
    execute: Callable = Field(..., description="The extension's execution function")
    schema_class: Optional[BaseModel] = Field(
        None, description="The schema class for the extension"
    )


def get_session_id(session: ContextVar) -> str:
    pre_session = session.get()
    session_id = pre_session.id if pre_session else str(uuid.uuid4())
    return session_id


def get_project_folder(session_id: str):
    dotenv.load_dotenv()
    project_folders = os.environ.get("PROJECT_FOLDERS", "./projects")
    project_folder = os.path.abspath(os.path.join(project_folders, session_id))
    os.makedirs(project_folder, exist_ok=True)

    return project_folder


def convert_to_dict(obj):
    if isinstance(obj, BaseModel):
        return obj.dict()
    if isinstance(obj, dict):
        return {k: convert_to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_to_dict(v) for v in obj]
    return obj


async def legacy_extension_to_tool(extension: LegacyChatbotExtension):
    if extension.get_schema:
        schema = await extension.get_schema()
        extension.schema_class = json_schema_to_pydantic_model(schema)
    else:
        input_schemas, _ = extract_schemas(extension.execute)
        extension.schema_class = input_schemas[0]

    assert (
        extension.schema_class
    ), f"Extension {extension.name} has no valid schema class."

    # NOTE: Right now, the first arguments has to be req
    async def execute(req: Any):
        print("Executing extension:", extension.name, req)
        # req = extension.schema_class.parse_obj(req)
        result = await extension.execute(req)
        return convert_to_dict(result)

    execute.__name__ = extension.name

    if extension.get_schema:
        execute.__doc__ = schema["description"]

    if not execute.__doc__:
        # if extension.execute is partial
        if hasattr(extension.execute, "func"):
            execute.__doc__ = extension.execute.func.__doc__ or extension.description
        else:
            execute.__doc__ = extension.execute.__doc__ or extension.description
    return schema_tool(execute)
