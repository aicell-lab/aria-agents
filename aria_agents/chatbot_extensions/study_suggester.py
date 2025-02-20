import argparse
import asyncio
from typing import Callable, Dict
from pydantic import BaseModel, Field
from schema_agents import schema_tool
from aria_agents.chatbot_extensions.aux import (
    SuggestedStudy,
    test_pmc_query_hits,
    create_corpus_function,
    write_website,
    ask_agent,
)
from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.utils import (
    get_query_index_dir,
    get_query_function,
    save_file,
    get_file,
    call_agent,
)


class StudyDiagram(BaseModel):
    """A diagram written in mermaid.js showing the workflow for the study and what expected data from the study will look like. An example:
    ```
    graph TD
    X[Cells] --> |Culturing| A
    A[Aniline Exposed Samples] -->|With NAC| B[Reduced Hepatotoxicity]
    A -->|Without NAC| C[Increased Hepatotoxicity]
    B --> D[Normal mmu_circ_26984 Levels]
    C --> E[Elevated mmu_circ_26984 Levels]
    style D fill:#4CAF50
    style E fill:#f44336
    ```
    Do not include specific conditions, temperatures, times, or other specific experimental protocol conditions just the general workflow and expected outcomes (for example, instead of 40 degrees say "high temperature").
    Do not include any special characters, only simple ascii characters.
    """

    diagram_code: str = Field(
        description="The code for a mermaid.js figure showing the study workflow and what the expected outcomes would look like for the experiment"
    )


class StudyWithDiagram(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge information from the literature review"""

    suggested_study: SuggestedStudy = Field(
        description="The suggested study to test a new hypothesis"
    )
    study_diagram: StudyDiagram = Field(
        description="The diagram illustrating the workflow for the suggested study"
    )


def create_pubmed_query_function(
    artifact_manager: AriaArtifacts = None,
    config: Dict = None,
) -> Callable:
    @schema_tool
    async def query_pubmed(
        user_request: str = Field(
            description="The user's request to create a study around, framed in terms of a scientific question"
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        ),
    ) -> str:
        """Create a corpus of papers from PubMed Central based on the user's request."""
        event_bus = artifact_manager.get_event_bus() if artifact_manager else None
        llm_model = config["llm_model"]

        await call_agent(
            name="NCBI Querier",
            instructions="You are the PubMed querier. You take the user's input and use it to create a query to search PubMed Central for relevant papers.",
            messages=[
                """Take the following user request and generate at least 5 different queries in the schema of 'PMCQuery' to search PubMed Central for relevant papers. 
                Ensure that all queries include the filter for open access papers. Test each query using the `test_pmc_query_hits` tool to determine which query returns the most hits. 
                If no queries return hits, adjust the queries to be more general (for example, by removing the `[Title/Abstract]` field specifications from search terms), and try again.
                Once you have identified the query with the highest number of hits, use it to create a corpus of papers with the `create_pubmed_corpus`.""",
                user_request,
            ],
            llm_model=llm_model,
            event_bus=event_bus,
            constraints=constraints,
            tools=[test_pmc_query_hits, create_corpus_function(artifact_manager, config)],
        )

        return "query_function created."

    return query_pubmed


# TODO: improve relevance and usefulness of citations
def create_study_suggester_function(
    config: Dict,
    artifact_manager: AriaArtifacts = None,
) -> Callable:
    llm_model = config["llm_model"]

    @schema_tool
    async def run_study_suggester(
        user_request: str = Field(
            description="The user's request to create a study around, framed in terms of a scientific question"
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        ),
    ) -> Dict[str, str]:
        """BEFORE USING THIS FUNCTION YOU NEED TO CREATE A QUERY_FUNCTION FROM THE `query_pubmed` TOOL. Create a study suggestion based on the user's request. This includes a literature review, a suggested study, and a summary website."""
        event_bus = artifact_manager.get_event_bus() if artifact_manager else None
        query_index_dir = get_query_index_dir(artifact_manager)
        query_function = get_query_function(query_index_dir, config)

        suggested_study = await call_agent(
            name="Study Suggester",
            instructions="You are the study suggester. You suggest a study to test a new hypothesis based on the cutting-edge information from the literature review.",
            messages=[
                f"Design a study to address an open question in the field based on the following user request: ```{user_request}```",
                "You have access to an already-collected corpus of PubMed papers and the ability to query it. If you don't get good information from your query, try again with a different query. You can get more results from maker your query more generic or more broad. Keep going until you have a good answer. You should try at the very least 5 different queries",
                "After generating the study, you will make a call to CompleteUserQuery. You should call that function with schema {'response': <SuggestedStudy>}.",
            ],
            tools=[query_function],
            output_schema=SuggestedStudy,
            llm_model=llm_model,
            event_bus=event_bus,
            constraints=constraints,
        )

        summary_website_url = await write_website(
            suggested_study,
            artifact_manager,
            "suggested_study",
            llm_model,
        )

        suggested_study_url = await save_file(
            "suggested_study.json", suggested_study.model_dump_json(), artifact_manager
        )

        return {
            "summary_website_url": summary_website_url,
            "suggested_study_url": suggested_study_url,
        }

    return run_study_suggester


def create_create_diagram_function(
    artifact_manager: AriaArtifacts = None,
    llm_model: str = "gpt2",
) -> Callable:
    @schema_tool
    async def create_diagram(
        suggested_study: SuggestedStudy = Field(
            description="The suggested study to test a new hypothesis. Generated by the `AriaStudySuggester` tool."
        ),
    ) -> Dict[str, str]:
        """BEFORE USING THIS FUNCTION YOU NEED TO GET A SUGGESTED STUDY FROM THE `AriaStudySuggester` TOOL. Create a diagram illustrating the workflow for the suggested study."""
        event_bus = artifact_manager.get_event_bus() if artifact_manager else None
        study_diagram = await ask_agent(
            name="Diagrammer",
            instructions="You are the diagrammer. You create a diagram illustrating the workflow for the suggested study.",
            messages=[
                f"Create a diagram illustrating the workflow for the suggested study:\n`{suggested_study.experiment_name}`",
                suggested_study,
            ],
            output_schema=StudyDiagram,
            llm_model=llm_model,
            event_bus=event_bus,
        )

        study_with_diagram = StudyWithDiagram(
            suggested_study=suggested_study, study_diagram=study_diagram
        )

        summary_website_url = await write_website(
            study_with_diagram, artifact_manager, "suggested_study", llm_model
        )
        study_with_diagram_url = await save_file(
            "study_with_diagram.json",
            study_with_diagram.model_dump_json(),
            artifact_manager,
        )

        return {
            "summary_website_url": summary_website_url,
            "study_with_diagram_url": study_with_diagram_url,
        }

    return create_diagram


def create_summary_website_function(
    artifact_manager: AriaArtifacts = None,
    llm_model: str = "gpt2",
) -> Callable:
    @schema_tool
    async def create_summary_website() -> Dict[str, str]:
        """BEFORE USING THIS FUNCTION YOU NEED TO GET A STUDY DIAGRAM FROM THE `create_diagram` TOOL. Create a summary website for the suggested study."""
        study_with_diagram_content = await get_file(
            "study_with_diagram.json", artifact_manager
        )
        study_with_diagram = StudyWithDiagram(**study_with_diagram_content)
        summary_website_url = await write_website(
            study_with_diagram,
            artifact_manager,
            "suggested_study",
            llm_model,
        )

        return {
            "summary_website_url": summary_website_url,
        }

    return create_summary_website


async def main():
    parser = argparse.ArgumentParser(description="Run the study suggester pipeline")
    parser.add_argument(
        "--user_request",
        type=str,
        help="The user request to create a study around",
        required=True,
    )
    parser.add_argument(
        "--constraints",
        type=str,
        help="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        default="",
    )
    args = parser.parse_args()
    artifact_manager = None

    run_study_suggester = create_study_suggester_function(artifact_manager)
    await run_study_suggester(**vars(args))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (RuntimeError, ValueError, IOError) as e:
        print(e)
