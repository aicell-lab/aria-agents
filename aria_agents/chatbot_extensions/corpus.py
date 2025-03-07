from typing import List, Optional
from pydantic import BaseModel, Field
from schema_agents import schema_tool
from aria_agents.utils import (
    SchemaToolReturn,
    ArtifactFile,
    is_artifacts_available,
    StatusCode,
)


class CorpusFile(BaseModel):
    """A file in the corpus"""

    name: str = Field(description="Name of the file")
    content: str = Field(description="Content of the file")


@schema_tool
async def list_corpus() -> SchemaToolReturn:
    """List all files in the current chat's corpus that can be loaded"""
    if not is_artifacts_available():
        return SchemaToolReturn(
            response="No artifact manager available",
            status=StatusCode.bad_request("No artifact manager available"),
        )

    return SchemaToolReturn(
        response="/list_corpus",
        status=StatusCode.ok("Command to list corpus files sent"),
    )


@schema_tool
async def get_corpus(
    file_paths: List[str] = Field(
        description="List of file paths in the corpus to retrieve"
    ),
) -> SchemaToolReturn:
    """Get contents of specific files from the corpus"""
    if not is_artifacts_available():
        return SchemaToolReturn(
            response="No artifact manager available",
            status=StatusCode.bad_request("No artifact manager available"),
        )

    return SchemaToolReturn(
        response=f"/get_corpus {','.join(file_paths)}",
        status=StatusCode.ok("Command to get corpus files sent"),
    )


@schema_tool
async def add_to_corpus(
    file_name: str = Field(description="Name of the file to save to the corpus"),
    content: str = Field(description="Content to save in the file"),
    model: Optional[str] = Field(
        None,
        description="Name of the BaseModel class if this content was created from one",
    ),
) -> SchemaToolReturn:
    """Add a new file to the corpus"""
    if not is_artifacts_available():
        error_msg = (
            f"Cannot add file '{file_name}' to corpus: No artifact manager available"
        )
        return SchemaToolReturn(
            response=error_msg, status=StatusCode.bad_request(error_msg)
        )

    artifact = ArtifactFile(name=file_name, content=content, model=model)

    success_msg = f"Successfully added file '{file_name}' to corpus"
    return SchemaToolReturn(
        response=success_msg, to_save=[artifact], status=StatusCode.created(success_msg)
    )
