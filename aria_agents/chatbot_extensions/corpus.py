from typing import List, Optional
from pydantic import BaseModel, Field
from schema_agents import schema_tool
from schema_agents.utils.common import EventBus
from aria_agents.utils import SchemaToolReturn, ArtifactFile, is_frontend_available

class CorpusFile(BaseModel):
    """A file in the corpus"""
    name: str = Field(description="Name of the file")
    content: str = Field(description="Content of the file")

class CorpusList(BaseModel):
    """List of files in the corpus"""
    files: List[str] = Field(description="List of file paths in the corpus")

class CorpusContent(BaseModel):
    """Content of requested corpus files"""
    contents: List[CorpusFile] = Field(description="List of files and their contents")
    failed: List[str] = Field(description="List of files that failed to be retrieved")

def create_list_corpus_function(event_bus: Optional[EventBus] = None) -> callable:
    @schema_tool
    async def list_corpus() -> SchemaToolReturn:
        """List all files in the current chat's corpus that can be loaded"""
        if not is_frontend_available():
            return SchemaToolReturn.error("No frontend available", 400)

        if not event_bus:
            return SchemaToolReturn.error("No event bus available", 400)

        try:
            result = await event_bus.emit("list_corpus")
            corpus_list = CorpusList(**result)
            
            file_list = "\n".join([f"- {f}" for f in corpus_list.files])
            file_count = len(corpus_list.files)
            
            return SchemaToolReturn.success(
                response=corpus_list,
                message=f"Found {file_count} files in corpus",
                to_save=[]
            )
        except Exception as e:
            return SchemaToolReturn.error(f"Failed to list corpus: {str(e)}", 500)

    return list_corpus

def create_get_corpus_function(event_bus: Optional[EventBus] = None) -> callable:
    @schema_tool
    async def get_corpus(
        file_paths: List[str] = Field(
            description="List of file paths in the corpus to retrieve"
        ),
    ) -> SchemaToolReturn:
        """Get contents of specific files from the corpus"""
        if not is_frontend_available():
            return SchemaToolReturn.error("No frontend available", 400)

        if not event_bus:
            return SchemaToolReturn.error("No event bus available", 400)

        try:
            result = await event_bus.emit("get_corpus", {"file_paths": file_paths})
            content = CorpusContent(**result)
            
            if not content.contents and content.failed:
                # All files failed
                return SchemaToolReturn.error(
                    f"Failed to retrieve files: {', '.join(content.failed)}",
                    404
                )
            
            if content.failed:
                # Partial success
                return SchemaToolReturn(
                    response=content,
                    status=StatusCode(
                        code=206,
                        type="success",
                        message=f"Retrieved {len(content.contents)} files, {len(content.failed)} failed"
                    )
                )
            
            # Complete success
            return SchemaToolReturn.success(
                response=content,
                message=f"Successfully retrieved {len(content.contents)} files"
            )

        except Exception as e:
            return SchemaToolReturn.error(f"Failed to retrieve files: {str(e)}", 500)

    return get_corpus

def create_add_to_corpus_function(event_bus: Optional[EventBus] = None) -> callable:
    @schema_tool
    async def add_to_corpus(
        file_name: str = Field(
            description="Name of the file to save to the corpus"
        ),
        content: str = Field(
            description="Content to save in the file"
        ),
        model: Optional[str] = Field(
            None,
            description="Name of the BaseModel class if this content was created from one"
        )
    ) -> SchemaToolReturn:
        """Add a new file to the corpus"""
        if not is_frontend_available():
            return SchemaToolReturn.error(
                f"Cannot add file '{file_name}' to corpus: No frontend available",
                400
            )

        artifact = ArtifactFile(
            name=file_name,
            content=content,
            model=model
        )

        return SchemaToolReturn.success(
            response=f"Successfully added file '{file_name}' to corpus",
            to_save=[artifact],
            message=f"File '{file_name}' created in corpus"
        )

    return add_to_corpus