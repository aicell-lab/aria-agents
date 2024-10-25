import json
import os
import uuid
from typing import Callable, List
import urllib
import xml.etree.ElementTree as xml
import requests

from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.readers.papers import PubmedReader
from pydantic import BaseModel, Field
from schema_agents import Role, schema_tool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session

from aria_agents.hypha_store import HyphaDataStore

# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "config.json")
with open(config_file, "r", encoding="utf-8") as file:
    CONFIG = json.load(file)


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
        description="The reasoning behind the choice of this experiment including the relevant background and pointers to references."
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
def test_pmc_query_hits(
    pmc_query: PMCQuery = Field(
        ..., description="The query to search the NCBI PubMed Central Database."
    )
) -> str:
    """Tests the `PMCQuery` to see how many hits it returns in the PubMed Central database."""

    parameters = {
        "tool": "tool",
        "email": "email",
        "db": "pmc",
        "term": pmc_query.query,
        "retmax": CONFIG["aux"]["paper_limit"],
    }
    resp = requests.get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        params=parameters,
        timeout=500,
    )

    # Parse the XML response
    root = xml.fromstring(resp.content)

    # Extract the number of hits from the <Count> element
    n_hits = len([elem for elem in root.iter() if elem.tag == "Id"])

    return f"The query `{pmc_query.query}` returned {n_hits} hits."


def create_corpus_function(
    context: dict, project_folder: str, data_store: HyphaDataStore = None
) -> Callable:
    @schema_tool
    def create_pubmed_corpus(
        pmc_query: PMCQuery = Field(
            ...,
            description="The query to search the NCBI PubMed Central Database.",
        )
    ) -> str:
        """Searches PubMed Central using `PMCQuery` and creates a citation query engine."""
        loader = PubmedReader()
        terms = urllib.parse.urlencode({"term": pmc_query.query, "db": "pmc"})
        print(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{terms}"
        )
        # print(test_pmc_query_hits(pmc_query))
        documents = loader.load_data(
            search_query=pmc_query.query,
            max_results=CONFIG["aux"]["paper_limit"],
        )
        if len(documents) == 0:
            return "No papers were found in the PubMed Central database for the given query. Please try different terms for the query."
        Settings.llm = OpenAI(model=CONFIG["llm_model"])
        Settings.embed_model = OpenAIEmbedding(
            model=CONFIG["aux"]["embedding_model"]
        )
        query_index = VectorStoreIndex.from_documents(documents)

        # Save the query index to disk
        query_index_dir = os.path.join(project_folder, "query_index")
        query_index.storage_context.persist(query_index_dir)
        if data_store is not None:
            project_name = os.path.basename(project_folder)
            data_store.put(
                obj_type="file",
                value=query_index_dir,
                name=f"{project_name}:pubmed_index_dir",
            )

        # Create a citation query engine object
        context["query_engine"] = CitationQueryEngine.from_args(
            query_index,
            similarity_top_k=CONFIG["aux"]["similarity_top_k"],
            citation_chunk_size=CONFIG["aux"]["citation_chunk_size"],
        )
        return f"Pubmed corpus with {len(documents)} papers has been created."

    return create_pubmed_corpus


def create_query_function(query_engine: CitationQueryEngine) -> Callable:
    @schema_tool
    def query_corpus(
        question: str = Field(
            ...,
            description="The query statement the LLM agent will answer based on the papers in the corpus. The question should not be overly specific or wordy. More general queries containing keywords will yield better results.",
        )
    ) -> str:
        """Given a corpus of papers created from a PubMedCentral search, queries the corpus and returns the response from the LLM agent"""
        response = query_engine.query(question)
        response_str = f"""The following query was run for the literature review:\n```{question}```\nA review of the literature yielded the following suggestions:\n```{response.response}```\n\nThe citations refer to the following papers:"""
        for i_node, node in enumerate(response.source_nodes):
            response_str += f"\n[{i_node + 1}] - {node.metadata['URL']}"
        print(response_str)
        return response_str

    return query_corpus


def load_template(template_file):
    with open(template_file, "r", encoding="utf-8") as file:
        return file.read()


async def write_website(
    input_model: BaseModel,
    event_bus,
    data_store,
    website_type: str,
    project_folder: str,
) -> SummaryWebsite:
    """Writes a summary website for the suggested study or experimental protocol"""
    website_writer = Role(
        name="Website Writer",
        instructions="You are the website writer. You create a single-page website summarizing the information in the suggested studies appropriately including the diagrams.",
        icon="🤖",
        constraints=None,
        event_bus=event_bus,
        register_default_events=True,
        model=CONFIG["llm_model"],
    )

    suggested_study_template = load_template(
        "html_templates/suggested_study_template.html"
    )
    exp_protocol_template = load_template(
        "html_templates/experimental_protocol_template.html"
    )
    website_prompt = None
    if website_type == "suggested_study":
        website_prompt = (
            "Create a single-page website summarizing the information in the"
            " suggested study using the following template:"
            f"\n{suggested_study_template}"
            "\nWhere the appropriate fields are filled in with the information from"
            " the suggested study."
        )
    elif website_type == "experimental_protocol":
        website_prompt = (
            "Create a single-page website summarizing the information in the experimental protocol"
            "website_prompt using the following template:"
            f"\n{exp_protocol_template}"
            "\nWhere the appropriate fields are filled in with the information from the experimental"
            "protocol."
        )

    pre_session = current_session.get()
    session_id = pre_session.id if pre_session else str(uuid.uuid4())

    async with create_session_context(
        id=session_id, role_setting=website_writer.role_setting
    ):
        summary_website = await website_writer.aask(
            [website_prompt, input_model],
            SummaryWebsite,
        )

    if data_store is None:
        # Save the summary website to a HTML file
        summary_website_file = os.path.join(
            project_folder, f"{website_type}.html"
        )
        with open(summary_website_file, "w", encoding="utf-8") as f:
            f.write(summary_website.html_code)
        summary_website_url = "file://" + summary_website_file
    else:
        # Save the summary website to the HyphaDataStore
        project_name = os.path.basename(project_folder)
        summary_website_id = data_store.put(
            obj_type="file",
            value=summary_website.html_code,
            name=f"{project_name}:{website_type}.html",
        )
        summary_website_url = data_store.get_url(summary_website_id)

    return summary_website_url
