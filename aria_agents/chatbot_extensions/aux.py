from pydantic import BaseModel, Field
from typing import List, Callable
import asyncio
import aiohttp
from schema_agents import schema_tool
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.core import VectorStoreIndex
from llama_index.readers.papers import PubmedReader

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

class SummaryWebsite(BaseModel):
    """A summary single-page webpage written in html that neatly presents the suggested study or experimental protocol for user review"""
    html_code: str = Field(description = "The html code for a single page website summarizing the information in the suggested study or experimental protocol appropriately including any diagrams. Make sure to include the original user request as well if available. References should appear as links (e.g. a url `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11129507/` can appear as a link with the name `PMC11129507` referencing the PMCID)")

class SuggestedStudy(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge"""
    user_request : str = Field(description = "The original user request")
    experiment_name : str = Field(description = "The name of the experiment")
    experiment_material : List[str] = Field(description = "The materials required for the experiment")
    experiment_expected_results : str = Field(description = "The expected results of the experiment")
    experiment_protocol : List[str] = Field(description = "The protocol steps for the experiment")
    experiment_hypothesis : str = Field(description = "The hypothesis to be tested by the experiment")
    experiment_reasoning : str = Field(description="The reasoning behind the choice of this experiment including the relevant background and pointers to references.")
    references : List[str] = Field(description="Citations and references to where these ideas came from. For example, point to specific papers or PubMed IDs to support the choices in the study design.")


async def call_api(base_url : str, params : dict) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(base_url, params=params) as response:
            if response.status == 200:
                return await response.text()
            else:
                raise Exception(f"NCBI API call request failed. Status code: {response.status}")


async def fetch_pmc_articles(pmcids : List[str]) -> str:
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pmc",      # Database: PubMed Central
        "rettype": "full", # Return type: Full article text
        "retmode": "xml", # Return mode: XML
        "id": ",".join(pmcids) # List of PMCIDs
    }
    return await call_api(base_url, params)

class PMCQuery(BaseModel):
    """A plain-text query to search the NCBI PubMed Central Database. It should follow standard NCBI search syntax for example 'cancer AND (mouse or monkey)'. 
To search in a specific journal (for example Bio-Protocol) use the term "Bio-protocol"[journal]". To search only open-access articles use the term "open access"[filter]"  """
    query : str = Field(description = "The query to search the NCBI PubMed Central Database")


PAPER_LIMIT = 20
LLM_MODEL = 'gpt-4o'
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_TOP_K = 5
CITATION_CHUNK_SIZE = 1024

@schema_tool
async def create_pubmed_corpus(pmc_query : PMCQuery = Field(..., description = "The query to search the NCBI PubMed Central Database")) -> CitationQueryEngine:
    """Searches the PubMed Central database using the `pmc_query` and returns a citation query engine object that can be used to query the papers found in the search results."""
    loader = PubmedReader()
    documents = loader.load_data(search_query = pmc_query.query, max_results = PAPER_LIMIT)
    Settings.llm = OpenAI(model = LLM_MODEL)
    Settings.embed_model = OpenAIEmbedding(model = EMBEDDING_MODEL)
    index = VectorStoreIndex.from_documents(documents)
    query_engine = CitationQueryEngine.from_args(
        index,
        similarity_top_k = SIMILARITY_TOP_K,
        citation_chunk_size = CITATION_CHUNK_SIZE,
    )
    return query_engine

def create_query_function(query_engine: CitationQueryEngine) -> Callable:
    @schema_tool
    async def query_corpus(question: str = Field(..., description="The question the LLM agent will answer based on the papers in the corpus. The question should not be overly specific or wordy. More general queries containing keywords will yield better results.")) -> str:
        """Given a corpus of papers created from a PubMedCentral search, queries the corpus with the given question and returns the response from the LLM agent"""
        response = query_engine.query(question)
        response_str = f"""The following question was asked for the literature review:\n```{question}```\nA review of the literature yielded the following suggestions:\n```{response.response}```\n\nThe citations refer to the following papers:"""
        for i_node, node in enumerate(response.source_nodes):
            response_str += f"\n[{i_node + 1}] - {node.metadata['URL']}"
        print(response_str)
        return response_str
    return query_corpus



@schema_tool
async def pmc_cited_search(pmc_query : PMCQuery = Field(..., description = "The query to search the NCBI PubMed Central Database"),
                     literature_question : str = Field(..., description = "The question to ask the LLM agent based on the papers found in the search results"),
                     ) -> str:
    """Searches the PubMed Central database using the `pmc_query`, gets the resulting paper content, and uses an LLM agent to answer the question `literature_question` based on the paper contents"""
    
    loader = PubmedReader()
    documents = loader.load_data(search_query = pmc_query.query, max_results = PAPER_LIMIT)
    Settings.llm = OpenAI(model = LLM_MODEL)
    Settings.embed_model = OpenAIEmbedding(model = EMBEDDING_MODEL)
    index = VectorStoreIndex.from_documents(documents)
    query_engine = CitationQueryEngine.from_args(
        index,
        similarity_top_k = SIMILARITY_TOP_K,
        citation_chunk_size = CITATION_CHUNK_SIZE,
    )
    response = query_engine.query(f"{literature_question}")
    response_str = f"""The following question was asked for the literature review:\n```{literature_question}```\nA review of the literature yielded the following suggestions:\n```{response.response}```\nAnd the citations refer to the following papers:"""
    for i_node, node in enumerate(response.source_nodes):
        response_str += f"\n[{i_node + 1}] - {node.metadata['URL']}"
    return response_str



@schema_tool
async def pmc_search(ncbi_query_url : str = Field(description = "The NCBI API web url to use for this query.")) -> str:
    """Uses the NCBI web API to search the PubMed Central (pmc) database."""
    query_response = await call_api(ncbi_query_url)
    query_response = query_response.decode()
    return query_response

@schema_tool
async def make_pmc_db(pmc_ids: List[str] = Field(description="The PubMed Central IDs of the articles")) -> str:
    """Bulk downloads a set of papers from the PubMed Central database given their IDs and creates a vector database to store the papers"""
    bulk_content = await fetch_pmc_articles(pmc_ids)
    


@schema_tool
async def pmc_efetch(pmc_ids: List[str] = Field(description="The PubMed Central IDs of the articles")) -> str:
    """Uses the NCBI Eutils API's efetch functionality to get in-depth information about a set of papers in the PubMed Central database given their IDs"""
    pmc_ids = ",".join(pmc_ids)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmc_ids}"
    query_response = await call_api(url)
    query_response = query_response.decode()
    return query_response