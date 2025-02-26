from typing import Dict, Callable, List
from pydantic import Field, BaseModel
from aria_agents.utils import schema_tool, call_agent
from aria_agents.artifact_manager import AriaArtifacts

class CorpusSearch(BaseModel):
    """The results of a corpus search"""

    results: List[str] = Field(
        description="The search results"
    )

    def __str__(self):
        return "\n".join(self.results)


def create_query_corpus(
    artifact_manager: AriaArtifacts = None,
) -> Callable:
    @schema_tool
    async def query_corpus(
        query: str = Field(
            description="The query to search for in the corpus"
        ),
    ) -> Dict[str, str]:
        corpus_results = await artifact_manager.search_vectors(query)

        return corpus_results

    return query_corpus