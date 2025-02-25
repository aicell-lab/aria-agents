import os
from typing import List

from pydantic import BaseModel, Field
from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.utils import save_file, ask_agent


class SummaryWebsite(BaseModel):
    """A summary single-page webpage written in html that neatly presents the suggested study or experimental protocol for user review"""

    html_code: str = Field(
        description=(
            "The html code for a single page website summarizing the information in the"
            " suggested study or experimental protocol appropriately including any"
            " diagrams. Make sure to include the original user request as well if"
            " available. References should appear as numbered links"
            " (e.g. a url`https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11129507/` can"
            " appear as a link with link text `[1]` referencing the link). Other sections of the text should refer to this reference by number"
        )
    )


class SuggestedStudy(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge literature review. Any time a reference is used anywhere, it MUST be cited directly, e.g. the specific sentence that uses the reference should include an annotation to that specific reference"""

    user_request: str = Field(
        description="The original user request. This MUST be included."
    )
    experiment_name: str = Field(description="The name of the experiment")
    experiment_material: List[str] = Field(
        description="The materials required for the experiment"
    )
    experiment_expected_results: str = Field(
        description="The expected results of the experiment"
    )
    # experiment_protocol : List[str] = Field(description = "The protocol steps for the experiment")
    experiment_workflow: str = Field(
        description="A high-level description of the workflow for the experiment. The steps should cite the references in the format of `[1]`, `[2]`, etc."
    )
    experiment_hypothesis: str = Field(
        description="The hypothesis to be tested by the experiment"
    )
    experiment_reasoning: str = Field(
        description=(
            "The reasoning behind the choice of this experiment including the"
            " relevant background and pointers to references."
        )
    )
    references: List[str] = Field(
        description="Citations and references to where these ideas came from. For example, point to specific papers or PubMed IDs to support the choices in the study design. Any time a reference is used in the other sections, the specific sentence MUST be linked specifically to one of these references. References should be numbered and numbering should be consistent with their appearances in other sections."
    )


def load_template(template_filename):
    this_dir = os.path.dirname(os.path.abspath(__file__))
    template_file = os.path.join(this_dir, f"html_templates/{template_filename}")
    with open(template_file, "r", encoding="utf-8") as t_file:
        return t_file.read()


def get_website_prompt(object_type):
    website_template = load_template(f"{object_type}_template.html")
    object_name = object_type.replace("_", " ").capitalize()
    return (
        f"Create a single-page website summarizing the information in the {object_name} using the following template:"
        f"\n{website_template}"
        f"\nWhere the appropriate fields are filled in with the information from the {object_name}."
    )


async def write_website(
    input_model: BaseModel,
    artifact_manager: AriaArtifacts,
    website_type: str,
    llm_model: str = "gpt2",
) -> SummaryWebsite:
    """Writes a summary website for the suggested study or experimental protocol"""
    event_bus = artifact_manager.get_event_bus()
    website_prompt = get_website_prompt(website_type)
        
    summary_website = await ask_agent(
        name="Website Writer",
        instructions="You are the website writer. You create a single-page website summarizing the information in the suggested studies appropriately including the diagrams.",
        messages=[website_prompt, input_model],
        output_schema=SummaryWebsite,
        llm_model=llm_model,
        event_bus=event_bus,
    )

    summary_website_url = await save_file(f"{website_type}.html", summary_website.html_code, artifact_manager)

    return summary_website_url
