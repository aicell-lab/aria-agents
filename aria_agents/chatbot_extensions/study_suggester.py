import argparse
import asyncio
from typing import List, Callable, Dict, Optional
from pydantic import BaseModel, Field
from schema_agents import schema_tool
from schema_agents.utils.common import current_session, EventBus
from aria_agents.chatbot_extensions.aux import (
    SuggestedStudy,
    write_website,
    ask_agent,
)
from aria_agents.utils import (
    call_agent,
    SchemaToolReturn,
    ArtifactFile,
    load_config,
    StatusCode
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
    """A suggested study with its workflow diagram"""
    suggested_study: SuggestedStudy = Field(
        description="The suggested study to test a new hypothesis"
    )
    study_diagram: StudyDiagram = Field(
        description="The diagram illustrating the workflow for the suggested study"
    )

class StudyResponse(BaseModel):
    """Response from the study suggester"""
    title: str = Field(description="Title of the study")
    description: str = Field(description="Study description")
    hypothesis: str = Field(description="Study hypothesis")
    workflow: str = Field(description="Study workflow")
    materials: List[str] = Field(description="Required materials")
    expected_results: str = Field(description="Expected results")
    reasoning: str = Field(description="Detailed reasoning")
    references: List[str] = Field(description="References used")

def create_study_suggester_function(config: Dict) -> Callable:
    llm_model = config["llm_model"]
    event_bus = config.get("event_bus")

    @schema_tool
    async def run_study_suggester(
        user_request: str = Field(
            description="The user's request to create a study around"
        ),
        constraints: str = Field(
            "",
            description="Optional constraints for the study"
        ),
    ) -> SchemaToolReturn:
        """Suggests a study to test a new hypothesis based on the user request."""
        try:
            suggested_study = await call_agent(
                name="Study Suggester",
                instructions="You are the study suggester. You suggest a study to test a new hypothesis based on the cutting-edge information from the literature review.",
                messages=[
                    f"Design a study to address an open question in the field based on the following user request: ```{user_request}```",
                    "After generating the study, you will make a call to CompleteUserQuery. You should call that function with schema {'response': <SuggestedStudy>}.",
                ],
                tools=[],
                output_schema=SuggestedStudy,
                llm_model=llm_model,
                event_bus=event_bus,
                constraints=constraints,
            )

            # Create study website content
            try:
                website_content = await write_website(suggested_study, event_bus, "suggested_study", llm_model)
            except Exception as e:
                return SchemaToolReturn(
                    to_save=[
                        ArtifactFile(
                            name="suggested_study.json",
                            content=suggested_study.model_dump_json(),
                            model="SuggestedStudy"
                        )
                    ],
                    response=suggested_study,
                    status=StatusCode(
                        code=206,
                        message="Study created but website generation failed",
                        type="success"
                    )
                )
            
            # Create response model
            response = StudyResponse(
                title=suggested_study.experiment_name,
                description=suggested_study.description,
                hypothesis=suggested_study.experiment_hypothesis,
                workflow=suggested_study.experiment_workflow,
                materials=suggested_study.experiment_material,
                expected_results=suggested_study.experiment_expected_results,
                reasoning=suggested_study.experiment_reasoning,
                references=suggested_study.references
            )
            
            return SchemaToolReturn(
                to_save=[
                    ArtifactFile(
                        name="suggested_study.json",
                        content=suggested_study.model_dump_json(),
                        model="SuggestedStudy"
                    ),
                    ArtifactFile(
                        name="study_website.html",
                        content=website_content
                    )
                ],
                response=response,
                status=StatusCode.created("Study and website created successfully")
            )
        except Exception as e:
            return SchemaToolReturn.error(f"Failed to generate study: {str(e)}", 500)

    return run_study_suggester

def create_diagram_function(llm_model: str = "gpt2", event_bus: Optional[EventBus] = None) -> Callable:
    @schema_tool
    async def create_diagram(
        suggested_study: SuggestedStudy = Field(
            description="The suggested study to create a diagram for"
        ),
    ) -> SchemaToolReturn:
        """Create a diagram illustrating the workflow for a study."""
        try:
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
                suggested_study=suggested_study,
                study_diagram=study_diagram
            )
            
            return SchemaToolReturn(
                to_save=[
                    ArtifactFile(
                        name="study_with_diagram.json",
                        content=study_with_diagram.model_dump_json(),
                        model="StudyWithDiagram"
                    )
                ],
                response=study_diagram,
                status=StatusCode.created("Study diagram created successfully")
            )
        except Exception as e:
            return SchemaToolReturn.error(f"Failed to create diagram: {str(e)}", 500)

    return create_diagram

def create_summary_website_function(
    llm_model: str,
    event_bus: Optional[EventBus] = None
) -> Callable:
    @schema_tool
    async def create_summary_website(
        study_with_diagram: StudyWithDiagram = Field(
            description="The study with its diagram to create a website for"
        ),
        llm_model: str = Field(
            "gpt2",
            description="The language model to use"
        ),
        event_bus: Optional[EventBus] = Field(
            None,
            description="Optional event bus for streaming"
        )
    ) -> SchemaToolReturn:
        """Create a summary website for a study with diagram. No wrapper needed since it's simple."""
        
        try:
            # Create website content
            website_content = await write_website(study_with_diagram, event_bus, "suggested_study", llm_model)
            
            return SchemaToolReturn(
                to_save=[
                    ArtifactFile(
                        name="study_website.html",
                        content=website_content
                    )
                ],
                response=study_with_diagram,
                status=StatusCode.created("Summary website created successfully")
            )
        except Exception as e:
            return SchemaToolReturn.error(f"Failed to create website: {str(e)}", 500)

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
        help="Specify any constraints that should be applied for compiling the experiments",
        default="",
    )
    args = parser.parse_args()
    config = load_config()

    run_study_suggester = create_study_suggester_function(config)
    await run_study_suggester(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
