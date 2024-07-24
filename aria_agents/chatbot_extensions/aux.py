import json
import os
import uuid
from typing import Callable, List

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
with open(config_file, "r") as file:
    CONFIG = json.load(file)


class SummaryWebsite(BaseModel):
    """A summary single-page webpage written in html that neatly presents the suggested study or experimental protocol for user review"""

    html_code: str = Field(
        description="The html code for a single page website summarizing the information in the suggested study or experimental protocol appropriately including any diagrams. Make sure to include the original user request as well if available. References should appear as links (e.g. a url `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11129507/` can appear as a link with the name `PMC11129507` referencing the PMCID)"
    )


class SuggestedStudy(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge"""

    user_request: str = Field(description="The original user request")
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


# async def call_api(base_url: str, params: dict) -> str:
#     async with aiohttp.ClientSession() as session:
#         async with session.get(base_url, params=params) as response:
#             if response.status == 200:
#                 return await response.text()
#             else:
#                 raise Exception(
#                     f"NCBI API call request failed. Status code: {response.status}"
#                 )


# async def fetch_pmc_articles(pmcids: List[str]) -> str:
#     base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
#     params = {
#         "db": "pmc",  # Database: PubMed Central
#         "rettype": "full",  # Return type: Full article text
#         "retmode": "xml",  # Return mode: XML
#         "id": ",".join(pmcids),  # List of PMCIDs
#     }
#     return await call_api(base_url, params)


class PMCQuery(BaseModel):
    """A plain-text query to search the NCBI PubMed Central Database. It should follow standard NCBI search syntax for example 'cancer AND (mouse or monkey)'.
    To search in a specific journal (for example Bio-Protocol) use the term "Bio-protocol"[journal]". To search only open-access articles use the term "open access"[filter]"
    """

    query: str = Field(
        description="The query to search the NCBI PubMed Central Database"
    )


def create_corpus_function(
    context: dict, project_folder: str, data_store: HyphaDataStore = None
) -> Callable:
    @schema_tool
    def create_pubmed_corpus(
        pmc_query: PMCQuery = Field(
            ..., description="The query to search the NCBI PubMed Central Database"
        )
    ) -> str:
        """Searches the PubMed Central database using the `pmc_query` and creates a citation query engine object that can be used to query the papers found in the search results."""
        loader = PubmedReader()
        documents = loader.load_data(pmc_query.query, CONFIG["aux"]["paper_limit"])
        Settings.llm = OpenAI(model=CONFIG["llm_model"])
        Settings.embed_model = OpenAIEmbedding(model=CONFIG["aux"]["embedding_model"])
        query_index = VectorStoreIndex.from_documents(documents)

        # Save the query index to disk
        query_index_dir = os.path.join(project_folder, "query_index")
        query_index.storage_context.persist(query_index_dir)
        if data_store is not None:
            project_name = os.path.basename(project_folder)
            query_index_dir_id = data_store.put(
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
        return "Pubmed corpus has been successfully created."

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


# @schema_tool
# def pmc_cited_search(
#     pmc_query: PMCQuery = Field(
#         ..., description="The query to search the NCBI PubMed Central Database"
#     ),
#     literature_question: str = Field(
#         ...,
#         description="The question to ask the LLM agent based on the papers found in the search results",
#     ),
# ) -> str:
#     """Searches the PubMed Central database using the `pmc_query`, gets the resulting paper content, and uses an LLM agent to answer the question `literature_question` based on the paper contents"""

#     loader = PubmedReader()
#     documents = loader.load_data(
#         search_query=pmc_query.query, max_results=CONFIG["aux"]["paper_limit"]
#     )
#     Settings.llm = OpenAI(model=CONFIG["llm_model"])
#     Settings.embed_model = OpenAIEmbedding(model=CONFIG["aux"]["embedding_model"])
#     index = VectorStoreIndex.from_documents(documents)
#     query_engine = CitationQueryEngine.from_args(
#         index,
#         similarity_top_k=CONFIG["aux"]["similarity_top_k"],
#         citation_chunk_size=CONFIG["aux"]["citation_chunk_size"],
#     )
#     response = query_engine.query(f"{literature_question}")
#     response_str = f"""The following question was asked for the literature review:\n```{literature_question}```\nA review of the literature yielded the following suggestions:\n```{response.response}```\nAnd the citations refer to the following papers:"""
#     for i_node, node in enumerate(response.source_nodes):
#         response_str += f"\n[{i_node + 1}] - {node.metadata['URL']}"
#     return response_str


# @schema_tool
# async def pmc_search(
#     ncbi_query_url: str = Field(
#         description="The NCBI API web url to use for this query."
#     ),
# ) -> str:
#     """Uses the NCBI web API to search the PubMed Central (pmc) database."""
#     query_response = await call_api(ncbi_query_url)
#     query_response = query_response.decode()
#     return query_response


# @schema_tool
# async def make_pmc_db(
#     pmc_ids: List[str] = Field(description="The PubMed Central IDs of the articles"),
# ) -> str:
#     """Bulk downloads a set of papers from the PubMed Central database given their IDs and creates a vector database to store the papers"""
#     bulk_content = await fetch_pmc_articles(pmc_ids)


# @schema_tool
# async def pmc_efetch(
#     pmc_ids: List[str] = Field(description="The PubMed Central IDs of the articles"),
# ) -> str:
#     """Uses the NCBI Eutils API's efetch functionality to get in-depth information about a set of papers in the PubMed Central database given their IDs"""
#     pmc_ids = ",".join(pmc_ids)
#     url = (
#         f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmc_ids}"
#     )
#     query_response = await call_api(url)
#     query_response = query_response.decode()
#     return query_response


async def write_website(
    input_model: BaseModel, event_bus, data_store, website_type: str, project_folder: str
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

    if website_type == "suggested_study":
        website_prompt = """Create a single-page website summarizing the information in the suggested study using the following template:
```
        <html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>`TITLE OF EXPERIMENT`</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #555; }
        p { line-height: 1.6; }
        ul { line-height: 1.6; }
        .diagram { margin-top: 20px; }
    </style>
    <!-- Include the Mermaid.js library -->
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({ startOnLoad: true });
    </script>
</head>
<body>
    <h1>`TITLE OF EXPERIMENT`</h1>
    <h2>User Request</h2>
    <p>`The original user request`</p>
    <h2>Hypothesis</h2>
    <p>`The hypothesis to be tested by the experiment`</p>
    <h2>Study Diagram</h2>
    <div class="mermaid">
        `The diagram illustrating the workflow for the suggested study`
    </div>
    <h2>Workflow</h2>
    <p>`A high-level description of the workflow for the experiment`</p>
    <h2>Reasoning</h2>
    <p>`The reasoning behind the choice of this experiment including the relevant background and pointers to references.`</p>
    <h2>Expected Results</h2>
    <p>`The expected results of the experiment`</p>
    <h2>Materials Required</h2>
    <ul>
        `The materials required for the experiment`
    </ul>
    <h2>References</h2>
    <ul>
        `Citations and references to where these ideas came from. For example, point to specific papers or PubMed IDs to support the choices in the study design. These can be referred to in other parts of the html`
    </ul>
</body>
</html>
```
Where the appropriate fields are filled in with the information from the suggested study.
        """

    elif website_type == "experimental_protocol":
        website_prompt = """Create a single-page website summarizing the information in the experimental protocol using the following template:
        ```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>`The title of the protocol`</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        h2 { color: #555; }
        p { line-height: 1.6; }
        ul { line-height: 1.6; }
        .diagram { margin-top: 20px; }
        a:hover { text-decoration: underline; }
        .section { margin-bottom: 40px; }
        .references { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>`The title of the protocol`</h1>

    <div class="section">
        <h2>`First Protocol Section name`</h2>
        <ol>
            `The protocol section steps`
        </ol>
        <div class="references">
            <h3>References</h3>
            <ul>
                `A list of references to existing protocols that the steps were taken from. These references should be in the form of URLs to the original protocol.`
            </ul>
        </div>
    </div>

    <div class="section">
        <h2>`Second Protocol Section name`</h2>
        <ol>
            `The protocol section steps`
        </ol>
        <div class="references">
            <h3>References</h3>
            <ul>
                `A list of references to existing protocols that the steps were taken from. These references should be in the form of URLs to the original protocol.`
            </ul>
        </div>
    </div>

    
    </div>
</body>
</html>
        ```
        Where the appropriate fields are filled in with the information from the experimental protocol.
        """

    pre_session = current_session.get()
    session_id = pre_session.id if pre_session else str(uuid.uuid4())

    async with create_session_context(
        id=session_id, role_setting=website_writer._setting
    ):
        summary_website = await website_writer.aask(
            [website_prompt, input_model],
            SummaryWebsite,
        )

    if data_store is None:
        # Save the summary website to a HTML file
        summary_website_file = os.path.join(project_folder, f"{website_type}.html")
        with open(summary_website_file, "w") as f:
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
