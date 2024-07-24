import dotenv

dotenv.load_dotenv()
import argparse
import asyncio
import json
import os
import uuid
from typing import Callable, Dict

from pydantic import BaseModel, Field
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session

from aria_agents.chatbot_extensions.aux import (
    PMCQuery,
    SuggestedStudy,
    create_corpus_function,
    create_query_function,
    write_website,
)
from aria_agents.hypha_store import HyphaDataStore

# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "config.json")
with open(config_file, "r") as file:
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


def create_study_suggester_function(data_store: HyphaDataStore = None) -> Callable:
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
    ) -> Dict[str, str]:
        """Create a study suggestion based on the user's request. This includes a literature review, a suggested study, and a summary website."""
        pre_session = current_session.get()
        session_id = pre_session.id if pre_session else str(uuid.uuid4())

        project_folders = os.environ.get("PROJECT_FOLDERS", "./projects")
        project_folder = os.path.abspath(os.path.join(project_folders, project_name))
        os.makedirs(project_folder, exist_ok=True)

        if data_store is None:
            event_bus = None
        else:
            event_bus = data_store.get_event_bus()

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
            id=session_id, role_setting=ncbi_querier._setting
        ):
            response = await ncbi_querier.acall(
                [
                    f"Take the following user request and use it construct a query to search PubMed Central for relevant papers. Limit your search to ONLY open access papers. Finally, use the PMCQuery to create a corpus of papers.",
                    user_request,
                ],
                tools=[
                    create_corpus_function(corpus_context, project_folder, data_store)
                ],
                thoughts_schema=PMCQuery,
            )

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
            id=session_id, role_setting=study_suggester._setting
        ):
            suggested_study = await study_suggester.acall(
                [
                    f"Design a study to address an open question in the field based on the following user request: ```{user_request}```",
                    "You have access to an already-collected corpus of PubMed papers and the ability to query it. If you don't get good information from your query, try again with a different query. You can get more results from maker your query more generic or more broad. Keep going until you have a good answer. You should try at the very least 5 different queries",
                ],
                tools=[query_function],
                output_schema=SuggestedStudy,
            )
        if data_store is None:
            # Save the suggested study to a JSON file
            suggested_study_file = os.path.join(project_folder, "suggested_study.json")
            with open(suggested_study_file, "w") as f:
                json.dump(suggested_study.dict(), f, indent=4)
            suggested_study_url = "file://" + suggested_study_file
        else:
            # Save the suggested study to the HyphaDataStore
            suggested_study_id = data_store.put(
                obj_type="json",
                value=suggested_study.dict(),
                name=f"{project_name}:suggested_study.json",
            )
            suggested_study_url = data_store.get_url(suggested_study_id)

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
            id=session_id, role_setting=study_suggester._setting
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

        summary_website_url = await write_website(
            study_with_diagram, event_bus, data_store, "suggested_study", project_folder
        )

        return {
            "summary_website_url": summary_website_url,
            "suggested_study_url": suggested_study_url,
        }

    return run_study_suggester


async def main():
    parser = argparse.ArgumentParser(description="Run the study suggester pipeline")
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

    # from imjoy_rpc.hypha import connect_to_server
    # server = await connect_to_server({"server_url": "https://ai.imjoy.io"})
    # data_store = HyphaDataStore()
    # await data_store.setup(server)
    data_store = None

    run_study_suggester = create_study_suggester_function(data_store)
    await run_study_suggester(**vars(args))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
