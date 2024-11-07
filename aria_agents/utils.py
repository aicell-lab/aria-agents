from typing import Any, Callable, Dict, Optional, _UnionGenericAlias
from inspect import signature
import requests
from tqdm import tqdm
from pydantic import BaseModel, Field
from schema_agents import schema_tool
from aria_agents.jsonschema_pydantic import json_schema_to_pydantic_model


def download_file(url, filename):
    response = requests.get(url, stream=True, timeout=500)
    file_size = int(response.headers.get("content-length", 0))

    # Initialize the progress bar
    progress = tqdm(
        response.iter_content(1024),
        f"Downloading {filename}",
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    )

    with open(filename, "wb") as f:
        for data in progress:
            # Update the progress bar
            progress.update(len(data))
            f.write(data)


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
    execute: Callable = Field(
        ..., description="The extension's execution function"
    )
    schema_class: Optional[BaseModel] = Field(
        None, description="The schema class for the extension"
    )


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
            execute.__doc__ = (
                extension.execute.func.__doc__ or extension.description
            )
        else:
            execute.__doc__ = extension.execute.__doc__ or extension.description
    return schema_tool(execute)


class QueryIndexer:
    """Singleton class for holding llama query index"""
    _instance = None
    query_index = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(QueryIndexer, cls).__new__(cls)
        return cls._instance