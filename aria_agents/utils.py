from contextvars import ContextVar
import os
import uuid
import json
from typing import Any, Callable, Dict, Optional, _UnionGenericAlias, List, Union, Type, Literal
from inspect import signature
import dotenv
from pydantic import BaseModel, Field, field_validator
from schema_agents.utils.common import current_session, EventBus
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from aria_agents.jsonschema_pydantic import json_schema_to_pydantic_model


class StatusCode(BaseModel):
    """Status information for a schema tool operation"""
    code: int = Field(description="HTTP-style status code. 2xx for success, 4xx for client errors, 5xx for server errors")
    message: str = Field(description="Human-readable status message")
    type: Literal["success", "error"] = Field(description="Type of status - success or error")

    @field_validator("type")
    @classmethod
    def set_type(cls, v, info):
        """Set the type based on the code"""
        code = info.data.get("code", 200)
        return "success" if code < 400 else "error"

    @classmethod
    def ok(cls, message: str = "Operation completed successfully") -> "StatusCode":
        """Create a success status"""
        return cls(code=200, message=message, type="success")

    @classmethod
    def created(cls, message: str = "Resource created successfully") -> "StatusCode":
        """Create a creation success status"""
        return cls(code=201, message=message, type="success")

    @classmethod
    def bad_request(cls, message: str) -> "StatusCode":
        """Create a client error status"""
        return cls(code=400, message=message, type="error")

    @classmethod
    def not_found(cls, message: str) -> "StatusCode":
        """Create a not found error status"""
        return cls(code=404, message=message, type="error")

    @classmethod
    def server_error(cls, message: str) -> "StatusCode":
        """Create a server error status"""
        return cls(code=500, message=message, type="error")


class ArtifactFile(BaseModel):
    """A file to be saved"""
    name: str = Field(description="Name of the file to save")
    content: str = Field(description="Content of the file to save")
    model: Optional[str] = Field(None, description="Name of the BaseModel class if this file was created from one")


class SchemaToolReturn(BaseModel):
    """Standardized return type for schema tools"""
    to_save: List[ArtifactFile] = Field(default=[], description="List of files to save")
    response: Union[str, BaseModel] = Field(description="The response to return, either as a string or a BaseModel")
    status: StatusCode = Field(
        default_factory=StatusCode.ok,
        description="Status information about the operation"
    )

    @classmethod
    def success(cls, response: Union[str, BaseModel], message: str = None, to_save: List[ArtifactFile] = None) -> "SchemaToolReturn":
        """Create a successful response"""
        return cls(
            response=response,
            to_save=to_save or [],
            status=StatusCode.ok(message if message else "Operation completed successfully")
        )

    @classmethod
    def error(cls, message: str, code: int = 400) -> "SchemaToolReturn":
        """Create an error response"""
        return cls(
            response=f"Error: {message}",
            to_save=[],
            status=StatusCode(code=code, message=message, type="error")
        )


async def call_agent(
    name: str,
    instructions: str,
    messages: List[str],
    llm_model: str,
    event_bus: Optional[EventBus] = None,
    tools: Optional[List] = None,
    output_schema: Optional[Type[BaseModel]] = None,
    constraints: Optional[str] = None,
) -> Any:
    """Call an agent and wait for its response"""
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
    name: str,
    instructions: str,
    messages: List,
    output_schema: Optional[Type[BaseModel]],
    llm_model: str,
    event_bus: Optional[EventBus] = None,
    constraints: Optional[str] = None,
) -> Any:
    """Ask an agent a question and wait for its response"""
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
        return obj.model_dump()
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
            execute.__doc__ = extension.execute.execute.func.__doc__ or extension.description
        else:
            execute.__doc__ = extension.execute.__doc__ or extension.description
    return schema_tool(execute)


def is_artifacts_available() -> bool:
    """Check if artifact manager is available through frontend.
    
    Returns:
        bool: True if artifact manager is available through frontend
    """
    session = current_session.get()
    if not session:
        return False
    role_setting = session.role_setting
    if not role_setting or not role_setting.get("extensions"):
        return False
    return any(ext.get("id") == "aria" for ext in role_setting["extensions"])
