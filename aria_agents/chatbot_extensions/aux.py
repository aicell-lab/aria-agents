import os
from typing import List, Optional
from pydantic import BaseModel, Field
from schema_agents.utils.common import EventBus
from aria_agents.utils import ask_agent

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
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge literature review. Any time a reference is used anywhere, it MUST be cited directly."""
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
    experiment_workflow: str = Field(
        description="A high-level description of the workflow for the experiment. References should be cited in the format of `[1]`, `[2]`, etc."
    )
    experiment_hypothesis: str = Field(
        description="The hypothesis to be tested by the experiment"
    )
    experiment_reasoning: str = Field(
        description="The reasoning behind the choice of this experiment including the relevant background and citations."
    )
    description: str = Field(
        description="A brief description of the study"
    )
    references: List[str] = Field(
        description="Citations and references to where these ideas came from. For example, point to specific papers or PubMed IDs to support the choices in the study design."
    )

def load_template(template_filename: str) -> str:
    """Load a website template file from the html_templates directory"""
    this_dir = os.path.dirname(os.path.abspath(__file__))
    template_file = os.path.join(this_dir, f"html_templates/{template_filename}")
    with open(template_file, "r", encoding="utf-8") as t_file:
        return t_file.read()

def get_website_prompt(object_type: str, template: str = None) -> str:
    """Get the prompt for website generation"""
    if template is None:
        template = load_template(f"{object_type}_template.html")
    object_name = object_type.replace("_", " ").capitalize()
    return (
        f"Create a single-page website summarizing the information in the {object_name} using the following template:"
        f"\n{template}"
        f"\nWhere the appropriate fields are filled in with the information from the {object_name}."
    )

async def write_website(
    input_model: BaseModel,
    event_bus: Optional[EventBus] = None,
    website_type: str = "suggested_study",
    llm_model: str = "gpt2",
    template: Optional[str] = None
) -> str:
    """Create a summary website for the suggested study or experimental protocol"""
    prompt = get_website_prompt(website_type, template)
    if template is None:
        template = load_template(f"{website_type}_template.html")

    summary_website = await ask_agent(
        name="Website Writer",
        instructions="You are a website writer. You write single-page websites that neatly present suggested studies or experimental protocols.",
        messages=[template, prompt, input_model],
        output_schema=SummaryWebsite,
        llm_model=llm_model,
        event_bus=event_bus,
    )

    return summary_website.html_code
