import argparse
import asyncio
from typing import Callable, Dict, List, Union, Optional
import dotenv
from pydantic import BaseModel, Field
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session, EventBus
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
    section_name: str = Field(description="The name of this section of the protocol")
    steps: List[str] = Field(description="The ordered list of steps in this section of the protocol")
    references: List[str] = Field(description="References supporting the steps in this section")

class ExperimentalProtocol(BaseModel):
    """A detailed list of steps outlining an experimental procedure that to be carried out in the lab. The steps MUST be detailed enough for a new student to follow them exactly without any questions or doubts.
    Do not include any data analysis portion of the study, only the procedure through the point of data collection. That means no statistical tests or data processing should be included unless they are necessary for downstream data collection steps."""
    protocol_title: str = Field(description="The title of the protocol")
    equipment: List[str] = Field(description="Equipment, materials, reagents needed for the protocol")
    sections: List[ProtocolSection] = Field(description="Ordered sections of the protocol")
    queries: List[str] = Field(default=[], description="A list of queries used to search for protocol steps in the paper corpus")

class ProtocolFeedback(BaseModel):
    """Expert scientist's feedback on a protocol"""
    complete: bool = Field(description="Whether the protocol is complete and ready to use")
    feedback_points: List[str] = Field(description="List of specific feedback points that need to be addressed")
    suggestions: List[str] = Field(description="Suggestions for improving the protocol, such as 'fetch new sources about cell culture techniques'")
    previous_feedback: str = Field("", description="Record of previous feedback that has been addressed")

async def write_protocol(
    protocol: Union[ExperimentalProtocol, SuggestedStudy],
    feedback: ProtocolFeedback,
    query_function: Callable,
    role: Role,
) -> ExperimentalProtocol:
    session_id = get_session_id(current_session)
    async with create_session_context(id=session_id, role_setting=role.role_setting):
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
    async with create_session_context(id=session_id, role_setting=role.role_setting):
        messages = [protocol]
        if feedback:
            messages.append(
                "Previous feedback that has been addressed:"
                f"\n{feedback.previous_feedback}"
            )

        messages.append(
            "You are an expert lab scientist reviewing this protocol. Your task is to:"
            "\n1. Verify that the protocol is complete and detailed enough for execution by a new student"
            "\n2. Check for any missing steps, unclear instructions, or insufficient detail"
            "\n3. Suggest improvements, including whether additional sources should be fetched for certain techniques"
            "\n4. Make sure all reagent concentrations, temperatures, timings and equipment settings are specified"
            "\n5. Ensure proper citation of reference protocols for key steps"
        )

        return await role.aask(messages, output_schema=ProtocolFeedback)

def create_experiment_compiler_function(
    config: Dict,
) -> Callable:
    llm_model = config["llm_model"]
    max_revisions = config["experiment_compiler"]["max_revisions"]

    @schema_tool
    async def run_experiment_compiler(
        suggested_study: SuggestedStudy = Field(
            description="The suggested study to generate an experimental protocol from"
        ),
        constraints: str = Field(
            "",
            description="Optional constraints to apply for compiling experiments"
        ),
        max_revisions: int = Field(
            default=max_revisions,
            description="Maximum number of protocol revision rounds"
        ),
    ) -> SchemaToolReturn:
        """Generate a detailed experimental protocol from a suggested study."""
        protocol_writer = Role(
            name="Protocol Writer",
            instructions="""You are a meticulous lab scientist who writes detailed, executable protocols. Your protocols must:
            1. Be specific enough that a new student could follow them exactly without questions
            2. Include all reagent concentrations, temperatures, timings, and equipment settings
            3. Cite reference protocols for key techniques using inline citations
            4. Focus only on data collection steps, not analysis
            5. Consider safety precautions and controls
            When feedback indicates missing information, you should suggest fetching new relevant sources.""",
            icon="🧬",
            constraints=constraints,
            model=llm_model,
        )

        if not suggested_study:
            return SchemaToolReturn.error(
                "A suggested study is required to generate an experimental protocol",
                400
            )

        # Initial protocol generation 
        messages = [
            {
                "role": "system",
                "content": f"""Take this suggested study and create a detailed experimental protocol. The protocol must:
                1. Include all steps needed for data collection (but not analysis)
                2. Specify exact quantities, times, temperatures, and equipment settings
                3. Include citations to reference protocols for key techniques
                4. Be clear enough for a new student to follow exactly
                Sugggested study:\n{suggested_study.model_dump_json()}"""
            }
        ]
        protocol = await protocol_writer.aask(messages, output_schema=ExperimentalProtocol)
        feedback = await get_protocol_feedback(protocol, protocol_writer)
        
        # Revision loop
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

        # Generate website content
        website_content = write_website(protocol, None, "experimental_protocol", llm_model)
        
        return SchemaToolReturn.success(
            response=protocol,
            message=f"Protocol generated after {revisions} revisions",
            to_save=[
                ArtifactFile(
                    name="experimental_protocol.json",
                    content=protocol.model_dump_json()
                ),
                ArtifactFile(
                    name="experimental_protocol.html",
                    content=website_content
                )
            ]
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
    config = load_config()

    run_experiment_compiler = create_experiment_compiler_function(config)
    await run_experiment_compiler(**vars(args))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (RuntimeError, ValueError, IOError) as e:
        print(e)
