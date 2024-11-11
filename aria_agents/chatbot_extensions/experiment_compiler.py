import argparse
import asyncio
import json
import os
import shutil
import uuid
from typing import Callable, Dict, List, Union
import dotenv
from llama_index.core import load_index_from_storage
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.core.storage import StorageContext
from pydantic import BaseModel, Field
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session
from tqdm.auto import tqdm
from aria_agents.chatbot_extensions.aux import (
    SuggestedStudy,
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


class ProtocolSection(BaseModel):
    """A section of an experimental protocol encompassing a specific set of steps falling under a coherent theme. The steps should be taken from existing protocols"""

    section_name: str = Field(..., description="The name of the section")
    steps: List[str] = Field(
        ...,
        description="A list of steps that must be followed in order to carry out the experiment.",
    )
    references: List[str] = Field(
        ...,
        description="A list of references to existing protocols that the steps were taken from. These references should be in the form of URLs to the original protocol.",
    )


class ExperimentalProtocol(BaseModel):
    """A detailed list of steps outlining an experimental procedure that to be carried out in the lab. The steps MUST be detailed enough for a new student to follow them exactly without any questions or doubts.
    Do not include any data analysis portion of the study, only the procedure through the point of data collection. That means no statistical tests or data processing should be included unless they are necessary for downstream data collection steps.
    """

    protocol_title: str = Field(..., description="The title of the protocol")
    # steps : List[str] = Field(..., description="A list of steps that must be followed in order to carry out the experiment. This string MUST be in markdown format and should contain no irregular characters.")
    equipment: List[str] = Field(
        ...,
        description="A list of equipment, materials, reagents, and devices needed for the entire protocol.",
    )
    sections: List[ProtocolSection] = Field(
        ...,
        description="A list of sections that must be followed in order to carry out the experiment.",
    )
    queries: List[str] = Field(
        ...,
        description="A list of queries that were previously used to search for the protocol steps in the paper corpus. Do not repeat queries across protocol revisions.",
    )


class ProtocolFeedback(BaseModel):
    """The expert scientist's feedback on a protocol"""

    complete: bool = Field(
        ...,
        description="Whether the protocol is specified in enough detail for a new student to follow it exactly without any questions or doubts",
    )
    feedback: str = Field(
        ..., description="The expert scientist's feedback on the protocol"
    )
    previous_feedback: List[str] = Field(
        ...,
        description="The previous feedback given to the protocol writer that has already been addressed.",
    )


async def get_protocol_feedback(
    protocol: ExperimentalProtocol,
    protocol_manager: Role,
    existing_feedback: ProtocolFeedback = None,
    session_id: str = None,
) -> ProtocolFeedback:
    if existing_feedback is None:
        pf = ProtocolFeedback(complete=False, feedback="", previous_feedback=[])
    else:
        pf = existing_feedback
    async with create_session_context(
        id=session_id, role_setting=protocol_manager.role_setting
    ):
        res = await protocol_manager.aask(
            [
                """Is the following protocol specified in enough detail for a new student to follow it exactly without any questions or doubts? If not, say why.
                                        First you will be given the previous feedback you wrote for this protocol then you will be given the current version of the protocol.
                                        If the previous feedback is non-empty, do not give redundant feedback, give new feedback that will help the protocol writer improve the protocol further and make sure to save the previous feedback into the `previous_feedback` field""",
                pf,
                protocol,
            ],
            output_schema=ProtocolFeedback,
        )
    return res


QUERY_TOOL_TIP = """Queries MUST not be of the form of a question, but rather in the form of the expected protocol chunk you are looking for because this will find closely matching sentences to your desired information.

# EXAMPLE QUERIES: 
- `CHO cells were cultured for 20 minutes`
- `supernatent was aspirated and cells were washed with PBS`
- `cells were lysed with RIPA buffer`
- `sample was centrifuged at 1000g for 5 minutes`
- `All tissue samples were pulverized using a ball mill (MM400, Retsch) with precooled beakers and stainless-steel balls for 30 s at the highest frequency (30 Hz)`
- `pulverized and frozen samples were extracted using the indicated solvents and subsequent steps of the respective protocol`
- `After a final centrifugation step the solvent extract of the protocols 100IPA, IPA/ACN and MeOH/ACN were transferred into a new 1.5 ml tube (Eppendorf) and snap-frozen until kit preparation.` 
- `The remaining protocols were dried using an Eppendorf Concentrator Plus set to no heat, stored at −80°C and reconstituted in 60 µL isopropanol (30 µL of 100% isopropanol, followed by 30 µL of 30% isopropanol in water) before the measurement.`"""


class CorpusQueries(BaseModel):
    """A list of queries to search against a given corpus of protocols"""

    queries: List[str] = Field(
        ...,
        description=f"A list of queries to search against a given corpus of protocols. {QUERY_TOOL_TIP}",
    )


class CorpusQueriesResponses(BaseModel):
    """A list of responses to queries made against a corpus of protocols"""

    responses: Dict[str, str] = Field(
        ...,
        description="A dictionary of responses to queries made against a corpus of protocols",
    )


async def write_protocol(
    protocol: Union[ExperimentalProtocol, SuggestedStudy],
    feedback: ProtocolFeedback,
    query_function: Callable,
    role: Role,
    session_id: str = None,
) -> ExperimentalProtocol:
    async with create_session_context(
        id=session_id, role_setting=role.role_setting
    ):
        if isinstance(protocol, SuggestedStudy):
            prompt = """Take the following suggested study and use it to produce a detailed protocol telling a student exactly what steps they should follow in the lab to collect data. Do not include any data analysis or conclusion-drawing steps, only data collection."""
            messages = [prompt, protocol]
            protocol_updated = await role.aask(
                messages, output_schema=ExperimentalProtocol
            )
        else:
            prompt = """You are being given a laboratory protocol that you have written and the feedback to make the protocol clearer for the lab worker who will execute it. First the protocol will be provided, then the feedback."""
            messages = [prompt, protocol, feedback]
            query_messages = [x for x in messages] + [
                "Use the feedback to produce a list of queries that you will use to search a given corpus of existing protocols for reference to existing steps in these protocols. Note the previous feedback and queries that you have already tried, and do not repeat them. Rather come up with new queries that will address the new feedback and improve the protocol further."
            ]
            queries = await role.aask(
                query_messages, output_schema=CorpusQueries
            )
            queries_responses = CorpusQueriesResponses(
                responses={
                    query: await query_function(query)
                    for query in queries.queries
                }
            )
            protocol_messages = [x for x in messages] + [
                "You searched a corpus of existing protocols for relevant steps in existing protocols and found the following responses",
                queries_responses,
                "Use these protocol corpus query responses to update and revise your protocol according to the feedback. Save the queries you used into the running list of previous queries. If a given query did not return a response from the corpus, do your best to update the protocol without the information from that single query using your internal knowledge or sources like protocols.io",
            ]
            protocol_updated = await role.aask(
                protocol_messages, output_schema=ExperimentalProtocol
            )
    return protocol_updated


def create_experiment_compiler_function(
    artifact_manager: ArtifactManager = None,
) -> Callable:
    @schema_tool
    async def run_experiment_compiler(
        project_name: str = Field(
            description="The name of the project, used to create a folder to store the output files and to read input files from the study suggester run"
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        ),
        max_revisions: int = Field(
            CONFIG["experiment_compiler"]["max_revisions"],
            description="The maximum number of protocol revision rounds to allow",
        ),
    ) -> Dict[str, str]:
        """Generate an investigation from a suggested study"""
        pre_session = current_session.get()
        session_id = pre_session.id if pre_session else str(uuid.uuid4())
        event_bus = None
        project_folders = os.environ.get("PROJECT_FOLDERS", "./projects")
        project_folder = os.path.abspath(
            os.path.join(project_folders, project_name)
        )
        query_index_dir = os.path.join(project_folder, "query_index")
        os.makedirs(query_index_dir, exist_ok=True)

        if artifact_manager is None:
            # Load the suggested study from a JSON file
            suggested_study_file = os.path.join(
                project_folder, "suggested_study.json"
            )
            with open(suggested_study_file, encoding="utf-8") as ss_file:
                suggested_study = SuggestedStudy(**json.load(ss_file))
        else:
            event_bus = artifact_manager.get_event_bus()
            suggested_study = await artifact_manager.get(f"{project_name}:suggested_study.json")
            await artifact_manager.get_dir(project_name, query_index_dir)

        query_storage_context = StorageContext.from_defaults(
            persist_dir=query_index_dir
        )
        
        if artifact_manager is not None:
            shutil.rmtree(query_index_dir, ignore_errors=True)
            
        query_index = load_index_from_storage(query_storage_context)
        query_engine = CitationQueryEngine.from_args(
            query_index,
            similarity_top_k=CONFIG["aux"]["similarity_top_k"],
            citation_chunk_size=CONFIG["aux"]["citation_chunk_size"],
        )
        query_function = create_query_function(query_engine)

        protocol_writer = Role(
            name="Protocol Writer",
            instructions="""You are an extremely detail oriented student who works in a biological laboratory. You read protocols and revise them to be specific enough until you and your fellow students could execute the protocol yourself in the lab.
        You do not conduct any data analysis, only data collection so your protocols only include steps up through the point of collecting data, not drawing conclusions.""",
            icon="🤖",
            constraints=constraints,
            event_bus=event_bus,
            register_default_events=True,
            model=CONFIG["llm_model"],
        )

        protocol_manager = Role(
            name="Protocol manager",
            instructions="You are an expert laboratory scientist. You read protocols and manage them to ensure that they are clear and detailed enough for a new student to follow them exactly without any questions or doubts.",
            icon="🤖",
            constraints=constraints,
            event_bus=event_bus,
            register_default_events=True,
            model=CONFIG["llm_model"],
        )

        protocol = await write_protocol(
            protocol=suggested_study,
            feedback=None,
            query_function=query_function,
            role=protocol_writer,
            session_id=session_id,
        )

        protocol_feedback = await get_protocol_feedback(
            protocol, protocol_manager, session_id=session_id
        )
        revisions = 0
        pbar = tqdm(total=max_revisions)

        while not protocol_feedback.complete and revisions < max_revisions:
            protocol = await write_protocol(
                protocol=protocol,
                feedback=protocol_feedback,
                query_function=query_function,
                role=protocol_writer,
                session_id=session_id,
            )

            protocol_feedback = await get_protocol_feedback(
                protocol,
                protocol_manager,
                protocol_feedback,
                session_id=session_id,
            )
            revisions += 1
            pbar.update(1)
        pbar.close()

        if artifact_manager is None:
            # Save the suggested study to a JSON file
            protocol_file = os.path.join(
                project_folder, "experimental_protocol.json"
            )
            with open(protocol_file, "w", encoding="utf-8") as f:
                json.dump(protocol.dict(), f, indent=4)
            protocol_url = "file://" + protocol_file

        else:
            # Save the suggested study to the Artifact Manager
            protocol_id = await artifact_manager.put(
                value=protocol.model_dump(),
                name=f"{project_name}:experimental_protocol.json",
            )
            protocol_url = await artifact_manager.get_url(session_id, protocol_id)

        summary_website_url = await write_website(
            protocol,
            event_bus,
            artifact_manager,
            "experimental_protocol",
            project_folder,
        )

        return {
            "summary_website_url": summary_website_url,
            "protocol_url": protocol_url,
        }

    return run_experiment_compiler


async def main():
    parser = argparse.ArgumentParser(description="Generate an investigation")
    parser.add_argument(
        "--project_name",
        type=str,
        help="The name of the project",
        default="test",
    )
    parser.add_argument(
        "--max_revisions",
        type=int,
        help="The maximum number of protocol agent revisions to allow",
        default=CONFIG["experiment_compiler"]["max_revisions"],
    )
    parser.add_argument(
        "--constraints",
        type=str,
        help="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        default="",
    )
    args = parser.parse_args()

    run_experiment_compiler = create_experiment_compiler_function()
    await run_experiment_compiler(**vars(args))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (RuntimeError, ValueError, IOError) as e:
        print(e)
