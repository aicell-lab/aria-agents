import argparse
import asyncio
from typing import Callable, Dict, List, Union
import dotenv
from pydantic import BaseModel, Field
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session
from aria_agents.chatbot_extensions.aux import (
    SuggestedStudy,
    write_website,
)
from aria_agents.utils import (
    load_config,
    get_session_id,
    SchemaToolReturn,
    ArtifactFile
)

dotenv.load_dotenv()

class ProtocolSection(BaseModel):
    """A section of an experimental protocol encompassing a specific set of steps falling under a coherent theme. The steps should be taken from existing protocols. When a step is taken from a reference protocol, you MUST include an inline citation. For example, in a section you might have the step `2. Wash cells in buffer for 30 minutes [2]` where `[2]` cites the reference protocol."""

    section_name: str = Field(..., description="The name of the section")
    steps: List[str] = Field(
        ...,
        description="A list of steps that must be followed in order to carry out the experiment. If you have used a reference for a step, you MUST link to the reference that you specifically used for this step.",
    )
    references: List[str] = Field(
        ...,
        description="A list of references to existing protocols that the steps were taken from. These references should be in numbered link forms of URLs to the original protocol. For example the link text should be something like `[2]` and the link content should link to the reference. The numbers should be consistent with how they are cited in other sections of this generated protocol.",
    )


class ExperimentalProtocol(BaseModel):
    """A detailed list of steps outlining an experimental procedure that to be carried out in the lab. The steps MUST be detailed enough for a new student to follow them exactly without any questions or doubts.
    Do not include any data analysis portion of the study, only the procedure through the point of data collection. That means no statistical tests or data processing should be included unless they are necessary for downstream data collection steps.
    """

    protocol_title: str = Field(..., description="The title of the protocol")
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


async def write_protocol(
    protocol: Union[ExperimentalProtocol, SuggestedStudy],
    feedback: ProtocolFeedback,
    query_function: Callable,
    role: Role,
) -> ExperimentalProtocol:
    session_id = get_session_id(current_session)
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
            query_messages = list(messages) + [
                "Based on the feedback, what queries would help you find information in the paper corpus to address the feedback?"
            ]
            queries = protocol.queries + [
                await query_function(query_messages),
            ]
            protocol_updated = await role.aask(
                messages + [await query_function(messages)],
                output_schema=ExperimentalProtocol,
            )
            protocol_updated.queries = queries

        return protocol_updated


async def get_protocol_feedback(
    protocol: ExperimentalProtocol,
    role: Role,
    feedback: ProtocolFeedback = None,
) -> ProtocolFeedback:
    session_id = get_session_id(current_session)
    async with create_session_context(
        id=session_id, role_setting=role.role_setting
    ):
        messages = [protocol]
        if feedback:
            messages.append(
                "Previous feedback that has already been addressed:"
                f"\n{feedback.previous_feedback}"
            )

        messages.append(
            "Please review the protocol and provide feedback on whether it is complete and detailed enough for a new student to follow it exactly."
        )

        return await role.aask(messages, output_schema=ProtocolFeedback)


def create_experiment_compiler_function(
    config: Dict,
    event_bus: Optional[EventBus] = None,
) -> Callable:
    llm_model = config["llm_model"]
    max_revisions = config["experiment_compiler"]["max_revisions"]
    query_index_dir = config["experiment_compiler"]["query_index_dir"]
    
    @schema_tool
    async def run_experiment_compiler(
        suggested_study: SuggestedStudy = Field(
            description="A suggested study to generate an experimental protocol from"
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        ),
        max_revisions: int = Field(
            default=max_revisions,
            description="The maximum number of protocol revision rounds to allow",
        ),
    ) -> SchemaToolReturn:
        """BEFORE USING THIS FUNCTION YOU NEED TO GET A STUDY SUGGESTION FROM THE AriaStudySuggester TOOL. Generate an investigation from a suggested study"""
        protocol_writer = Role(
            name="Protocol Writer",
            instructions="""You are an extremely detail oriented student who works in a biological laboratory. You read protocols and revise them to be specific enough until you and your fellow students could execute the protocol yourself in the lab.
            You do not conduct any data analysis, only data collection so your protocols only include steps up through the point of collecting data, not drawing conclusions.""",
            icon="🤖",
            constraints=constraints,
            event_bus=event_bus,
            register_default_events=True,
            model=llm_model,
        )

        protocol = await write_protocol(
            protocol=suggested_study,
            feedback=None,
            query_function=query_function,
            role=protocol_writer,
        )

        protocol_feedback = await get_protocol_feedback(
            protocol, protocol_writer
        )
        revisions = 0

        while not protocol_feedback.complete and revisions < max_revisions:
            protocol = await write_protocol(
                protocol=protocol,
                feedback=protocol_feedback,
                query_function=query_function,
                role=protocol_writer,
            )

            protocol_feedback = await get_protocol_feedback(
                protocol,
                protocol_writer,
                protocol_feedback,
            )
            revisions += 1
            
        website_content = write_website(protocol, None, "experimental_protocol", llm_model)
        
        return SchemaToolReturn(
            to_save=[
                ArtifactFile(
                    name="experimental_protocol.json",
                    content=protocol.model_dump_json()
                ),
                ArtifactFile(
                    name="experimental_protocol.html",
                    content=website_content
                )
            ],
            response={
                "protocol_title": protocol.protocol_title,
                "sections": [section.section_name for section in protocol.sections]
            }
        )

    return run_experiment_compiler


async def main():
    parser = argparse.ArgumentParser(description="Run the experiment compiler pipeline")
    parser.add_argument(
        "--constraints",
        type=str,
        help="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        default="",
    )
    args = parser.parse_args()
    artifact_manager = None
    config = load_config()

    run_experiment_compiler = create_experiment_compiler_function(config)
    await run_experiment_compiler(**vars(args))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (RuntimeError, ValueError, IOError) as e:
        print(e)
