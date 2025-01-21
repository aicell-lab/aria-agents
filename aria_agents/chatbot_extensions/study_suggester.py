import argparse
import asyncio
import json
import os
import uuid
from typing import Callable, Dict
import dotenv
from pydantic import BaseModel, Field
from aria_agents.utils import get_project_folder
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session
from aria_agents.chatbot_extensions.aux import (
    SuggestedStudy,
    test_pmc_query_hits,
    create_corpus_function,
    create_query_function,
    write_website,
)
from aria_agents.artifact_manager import ArtifactManager

dotenv.load_dotenv()

# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "config.json")
with open(config_file, "r", encoding="utf-8") as file:
    CONFIG = json.load(file)


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
    
def create_summary_website_function(
    artifact_manager: ArtifactManager = None,
) -> Callable:
    @schema_tool
    async def create_summary_website(
        suggested_study: SuggestedStudy = Field(
            description="The suggested study to test a new hypothesis"
        ),
        study_diagram: StudyDiagram = Field(
            description="The diagram illustrating the workflow for the suggested study"
        ),
        project_name: str = Field(
            description="The name of the project, used to create a folder to store the output files"
        ),
        study_with_diagram: StudyWithDiagram = Field(
            description="The suggested study with the diagram"
        ),
    ) -> Dict[str, str]:
        project_folder = get_project_folder(project_name)
        event_bus = None

        if artifact_manager is None:
            os.makedirs(project_folder, exist_ok=True)
        else:
            event_bus = artifact_manager.get_event_bus()

        summary_website_url = await write_website(
            study_with_diagram,
            event_bus,
            artifact_manager,
            "suggested_study",
            project_folder,
        )

        return summary_website_url,
    return create_summary_website

def create_pubmed_query_function(
    artifact_manager: ArtifactManager = None,
) -> Callable:
    @schema_tool
    async def query_pubmed(
        user_request: str = Field(
            description="The user's request to create a study around, framed in terms of a scientific question"
        ),
        project_name: str = Field(
            description="The name of the project, used to create a folder to store the output files"
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        ),
    ) -> Dict[str, str]:
        pre_session = current_session.get()
        session_id = pre_session.id if pre_session else str(uuid.uuid4())

        project_folder = get_project_folder(project_name)
        event_bus = None

        if artifact_manager is None:
            os.makedirs(project_folder, exist_ok=True)
        else:
            event_bus = artifact_manager.get_event_bus()
        
        ncbi_querier = Role(
            name="NCBI Querier",
            instructions="You are the PubMed querier. You take the user's input and use it to create a query to search PubMed Central for relevant papers.",
            icon="🤖",
            constraints=constraints,
            event_bus=event_bus,
            register_default_events=True,
            model=CONFIG["llm_model"],
        )

        corpus_context = {}
        async with create_session_context(
            id=session_id, role_setting=ncbi_querier.role_setting
        ):
            await ncbi_querier.acall(
                [
                    """Take the following user request and generate at least 5 different queries in the schema of 'PMCQuery' to search PubMed Central for relevant papers. 
                    Ensure that all queries include the filter for open access papers. Test each query using the `test_pmc_query_hits` tool to determine which query returns the most hits. 
                    If no queries return hits, adjust the queries to be more general (for example, by removing the `[Title/Abstract]` field specifications from search terms), and try again.
                    Once you have identified the query with the highest number of hits, use it to create a corpus of papers with the `create_pubmed_corpus`.""",
                    user_request,
                ],
                tools=[
                    test_pmc_query_hits,
                    create_corpus_function(
                        corpus_context, project_folder, artifact_manager
                    ),
                ],
            )
            
        return corpus_context
    return query_pubmed

@schema_tool
async def run_study_with_diagram(
    suggested_study: SuggestedStudy = Field(
        description="The suggested study to test a new hypothesis"
    ),
    role_setting: Dict[str, str] = Field(
        description="The role setting for the study diagrammer"
    ),
) -> Dict[str, str]:
    pre_session = current_session.get()
    session_id = pre_session.id if pre_session else str(uuid.uuid4())
    event_bus = None
    
    diagrammer = Role(
        name="Diagrammer",
        instructions="You are the diagrammer. You create a diagram illustrating the workflow for the suggested study.",
        icon="🤖",
        constraints=None,
        event_bus=event_bus,
        register_default_events=True,
        model=CONFIG["llm_model"],
    )
    async with create_session_context(
        id=session_id, role_setting=role_setting
    ):
        study_diagram = await diagrammer.aask(
            [
                f"Create a diagram illustrating the workflow for the suggested study:\n`{suggested_study.experiment_name}`",
                suggested_study,
            ],
            StudyDiagram,
        )
    study_with_diagram = StudyWithDiagram(
        suggested_study=suggested_study, study_diagram=study_diagram
    )
    
    return study_with_diagram

# TODO: improve relevancy and usefulness of citations
def create_study_suggester_function(
    artifact_manager: ArtifactManager = None,
) -> Callable:
    @schema_tool
    async def run_study_suggester(
        user_request: str = Field(
            description="The user's request to create a study around, framed in terms of a scientific question"
        ),
        project_name: str = Field(
            description="The name of the project, used to create a folder to store the output files"
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        ),
        corpus_context: Dict = Field(
            {},
            description="The context for the corpus of papers to be used for the study suggestion",
        ),
    ) -> Dict[str, str]:
        """Create a study suggestion based on the user's request. This includes a literature review, a suggested study, and a summary website."""
        pre_session = current_session.get()
        session_id = pre_session.id if pre_session else str(uuid.uuid4())

        project_folder = get_project_folder(project_name)
        event_bus = None

        if artifact_manager is None:
            os.makedirs(project_folder, exist_ok=True)
        else:
            event_bus = artifact_manager.get_event_bus()

        study_suggester = Role(
            name="Study Suggester",
            instructions="You are the study suggester. You suggest a study to test a new hypothesis based on the cutting-edge information from the literature review.",
            icon="🤖",
            constraints=constraints,
            event_bus=event_bus,
            register_default_events=True,
            model=CONFIG["llm_model"],
        )
        
        query_function = create_query_function(corpus_context["query_engine"])
        async with create_session_context(
            id=session_id, role_setting=study_suggester.role_setting
        ):
            suggested_study = await study_suggester.acall(
                [
                    f"Design a study to address an open question in the field based on the following user request: ```{user_request}```",
                    "You have access to an already-collected corpus of PubMed papers and the ability to query it. If you don't get good information from your query, try again with a different query. You can get more results from maker your query more generic or more broad. Keep going until you have a good answer. You should try at the very least 5 different queries",
                ],
                tools=[query_function],
                output_schema=SuggestedStudy,
            )
        if artifact_manager is None:
            # Save the suggested study to a JSON file
            suggested_study_file = os.path.join(
                project_folder, "suggested_study.json"
            )
            with open(suggested_study_file, "w", encoding="utf-8") as f:
                json.dump(suggested_study.dict(), f, indent=4)
            suggested_study_url = "file://" + suggested_study_file
        else:
            suggested_study_id = await artifact_manager.put(
                value=suggested_study.json(),
                name=f"{project_name}:suggested_study.json",
            )
            suggested_study_url = await artifact_manager.get_url(
                name=suggested_study_id
            )

        return suggested_study_url

    return run_study_suggester


async def main():
    parser = argparse.ArgumentParser(
        description="Run the study suggester pipeline"
    )
    parser.add_argument(
        "--user_request",
        type=str,
        help="The user request to create a study around",
        required=True,
    )
    parser.add_argument(
        "--project_name",
        type=str,
        help="The name of the project, used to create a folder to store the output files",
        default="test",
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
