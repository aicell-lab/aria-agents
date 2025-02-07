import os
import uuid
from typing import Callable, List
import urllib
import xml.etree.ElementTree as xml

import httpx
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.readers.papers import PubmedReader
from pydantic import BaseModel, Field
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session

from aria_agents.artifact_manager import AriaArtifacts
from aria_agents.utils import load_config, save_file, get_query_index_dir


class SummaryWebsite(BaseModel):
    """A summary single-page webpage written in html that neatly presents the suggested study or experimental protocol for user review"""

    html_code: str = Field(
        description=(
            "The html code for a single page website summarizing the information in the"
            " suggested study or experimental protocol appropriately including any"
            " diagrams. Make sure to include the original user request as well if"
            " available. References should appear as links"
            " (e.g. a url`https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11129507/` can"
            " appear as a link with the name `PMC11129507` referencing the PMCID)"
        )
    )


class SuggestedStudy(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge"""

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
        description="A high-level description of the workflow for the experiment"
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
        description="Citations and references to where these ideas came from. For example, point to specific papers or PubMed IDs to support the choices in the study design."
    )


class PMCQuery(BaseModel):
    """
    A plain-text query in a single-key dict formatted according to the NCBI search syntax. The query must include:

    1. Exact Match Terms: Enclose search terms in double quotes for precise matches. For example, `"lung cancer"` searches for the exact phrase "lung cancer".

    2. Boolean Operators: Use Boolean operators (AND, OR, NOT) to combine search terms. For instance, `"lung cancer" AND ("mouse" OR "monkey")`.

    3. Field Specification: Append `[Title/Abstract]` to each term to limit the search to article titles and abstracts. For example: `"rat"[Title/Abstract] OR "mouse"[Title/Abstract]`.

    4. Specific Journal Search: To restrict the search to articles from a particular journal, use the format `"[Journal Name]"[journal]`. For example, `"Bio-protocol"[journal]`.

    5. Open Access Filter: To filter results to only include open-access articles, add `"open access"[filter]` to the query.

    Example Query:
    ```
    {'query': '"lung cancer"[Title/Abstract] AND ("mouse"[Title/Abstract] OR "monkey"[Title/Abstract]) AND "Bio-protocol"[journal] AND "open access"[filter]'}
    ```
    """

    query: str = Field(
        description="The query to search the NCBI PubMed Central Database"
    )


@schema_tool
async def test_pmc_query_hits(
    pmc_query: PMCQuery = Field(
        ..., description="The query to search the NCBI PubMed Central Database."
    )
) -> str:
    """Tests the `PMCQuery` to see how many hits it returns in the PubMed Central database."""
    config = load_config()
    parameters = {
        "tool": "tool",
        "email": "email",
        "db": "pmc",
        "term": pmc_query.query,
        "retmax": config["aux"]["paper_limit"],
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params=parameters,
                timeout=500,
            )
            resp.raise_for_status()
    except Exception as e:
        return f"Failed to execute query: {e}"

    # Parse the XML response
    root = xml.fromstring(resp.content)

    # Extract the number of hits from the <Count> element
    n_hits = len([elem for elem in root.iter() if elem.tag == "Id"])

    return f"The query `{pmc_query.query}` returned {n_hits} hits."

async def save_query_index(query_index_dir, documents):
    query_index = VectorStoreIndex.from_documents(documents)
    query_index.storage_context.persist(query_index_dir)

def create_corpus_function(
    project_folder: str, artifact_manager: AriaArtifacts = None
) -> Callable:
    config = load_config()
    @schema_tool
    async def create_pubmed_corpus(
        pmc_query: PMCQuery = Field(
            ...,
            description="The query to search the NCBI PubMed Central Database.",
        )
    ) -> str:
        """Searches PubMed Central using `PMCQuery` and creates a citation query engine."""
        terms = urllib.parse.urlencode({"term": pmc_query.query, "db": "pmc"})
        print(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{terms}"
        )
        # Move more of this to save_query_index for async?
        loader = PubmedReader()
        # print(test_pmc_query_hits(pmc_query))
        documents = loader.load_data(
            search_query=pmc_query.query,
            max_results=config["aux"]["paper_limit"],
        )
        if len(documents) == 0:
            return "No papers were found in the PubMed Central database for the given query. Please try different terms for the query."
        Settings.llm = OpenAI(model=config["llm_model"])
        Settings.embed_model = OpenAIEmbedding(
            model=config["aux"]["embedding_model"]
        )
        print("Document loading complete")
        
        query_index_dir = get_query_index_dir(artifact_manager, project_folder)
        
        await save_query_index(query_index_dir, documents)
        
        return f"Pubmed corpus with {len(documents)} papers has been created."

    return create_pubmed_corpus


async def ask_agent(name, instructions, messages, output_schema, session_id, llm_model, event_bus = None, constraints = None):
    agent = Role(
        name=name,
        instructions=instructions,
        icon="🤖",
        constraints=constraints,
        event_bus=event_bus,
        register_default_events=True,
        model=llm_model,
    )
    async with create_session_context(
        id=session_id, role_setting=agent.role_setting
    ):
        return await agent.aask(
            messages,
            output_schema=output_schema,
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
    project_name: str,
) -> SummaryWebsite:
    """Writes a summary website for the suggested study or experimental protocol"""
    config = load_config()
    event_bus = artifact_manager.get_event_bus()
    website_prompt = get_website_prompt(website_type)
    pre_session = current_session.get()
    session_id = pre_session.id if pre_session else str(uuid.uuid4())
        
    summary_website = await ask_agent(
        name="Website Writer",
        instructions="You are the website writer. You create a single-page website summarizing the information in the suggested studies appropriately including the diagrams.",
        messages=[website_prompt, input_model],
        output_schema=SummaryWebsite,
        session_id=session_id,
        llm_model=config["llm_model"],
        event_bus=event_bus,
    )

    summary_website_url = await save_file(f"{website_type}.html", summary_website.html_code, project_name, artifact_manager)

    return summary_website_url
