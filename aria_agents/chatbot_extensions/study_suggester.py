import os
import dotenv
dotenv.load_dotenv()
import time
from tqdm.auto import tqdm
import argparse
from pydantic import BaseModel, Field
from typing import List
import asyncio
from schema_agents import schema_tool, Role
import dotenv
import re
import json
from aria_agents.chatbot_extensions.aux_classes import SuggestedStudy
from aria_agents.chatbot_extensions.aux_tools import *

import os
from llama_index.llms.openai import OpenAI
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.core import VectorStoreIndex
from llama_index.readers.papers import PubmedReader

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

class PapersSummary(BaseModel):
    """A summary of the papers found in the PubMed Central database search"""
    state_of_field : str = Field(description="A summary of the current state of the field")
    open_questions : str = Field(description="A summary of the open questions in the field")

class StructuredUserInput(BaseModel):
    """The user's input parsed scraped for relevant terms to search on pubmed"""
    user_request : str = Field(description = "The original user request")
    search_keywords : str = Field(description = "The keywords that will be used to search PubMed Central for recent relevant papers")

class StructuredQuery(BaseModel):
    """A query formatted to search the NCBI PubMed Central Database (open-access subset ONLY) inspired by the user's input query"""
    query: str = Field(description = "The NCBI PubMed query string, it MUST fit the NCBI PubMed database search syntax.")
    query_url: str = Field(description = """The query converted into a NCBI E-utils url. It must be only the url and it must folow the E-utils syntax. It should specify xml return mode, search the pmc database and the search MUST include `"+AND+open+access[filter]` to limit the search to open access articles.""")

class ContextualizedPaperSummary(BaseModel):
    """A short summary of a paper in the context of the user's request. ONLY include information that is relevant to the original user request."""
    state_of_field : str = Field(description="Brief summary of any information in the paper relating to the state of the field relevant to the user's request")
    open_questions : str = Field(description="Brief summary of any information in the paper relating to open questions in the field relevant to the user's request")
    
async def process_paper(pb, pmc_id, user_request, semaphore):
    async with semaphore:
        r = Role(name=f"Paper Agent PMC ID {pmc_id}",
                 instructions=f"You are an agent assigned to study the paper (PMC ID {pmc_id}) provided to you in the context of the user's request (`{user_request}`)",
                 constraints=None,
                 register_default_events=True,
                 model='gpt-4o')
        return await r.aask([f"The user wants to design a cutting-edge scientific study based on the original request:\n`{user_request}`\nRead the following paper's contents and scrape it for information relevant to designing a study for the user",
                             f"Paper content:\n`{pb}`"], ContextualizedPaperSummary)
    
class LiteratureReview(BaseModel):
    """A collection of summaries from papers found to be relevant to the user's request"""
    paper_summaries : List[ContextualizedPaperSummary] = Field(description = """The summaries from the individual papers""")

class StudyDiagram(BaseModel):
    """A diagram written in mermaid.js showing what the expected data from a study will look like"""
    diagram_code : str = Field(description = "The code for a mermaid.js diagram (either a XYChart, Pie, or QuadrantChart) showing what the expected data results would look like for the experiment")

class StudyWithDiagram(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge information from the literature review"""
    suggested_study : SuggestedStudy = Field(description = "The suggested study to test a new hypothesis")
    study_diagram : StudyDiagram = Field(description = "The diagram illustrating the workflow for the suggested study")

class SummaryWebsite(BaseModel):
    """A summary single-page webpage written in html that neatly presents the suggested study for user review"""
    html_code: str = Field(description = "The html code for a single page website summarizing the information in the suggested studies appropriately including the diagrams. Make sure to include the original user request as well. References should appear as links (e.g. a url `https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11129507/` can appear as a link with the name `PMC11129507` referencing the PMCID)")


class PMCQuery(BaseModel):
    """A plain-text query to search the NCBI PubMed Central Database. It should follow standard NCBI search syntax for example 'cancer AND (mouse or monkey)'. 
To search in a specific journal (for example Bio-Protocol) use the term "Bio-protocol"[journal]". To search only open-access articles use the term "open access"[filter]"  """
    query : str = Field(description = "The query to search the NCBI PubMed Central Database")



CONCURENCY_LIMIT = 3
PAPER_LIMIT = 5
LLM_MODEL = 'gpt-4o'
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_TOP_K = 5
CITATION_CHUNK_SIZE = 512
project_folders = os.environ.get('PROJECT_FOLDERS', './projects')
os.makedirs(project_folders, exist_ok = True)

@schema_tool
async def run_study_suggester(
    user_request: str = Field(description = "The user's request to create a study around, framed in terms of a scientific question"),
    project_name: str = Field(description = "The name of the project, used to create a folder to store the output files"),
    constraints: str = Field("", description = "Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc."),
):
    """Create a study suggestion based on the user's request. This includes a literature review, a suggested study, a diagram of the study, and a summary website."""

    project_folder = os.path.join(project_folders, project_name)
    os.makedirs(project_folder, exist_ok = True)
    ncbi_querier = Role(name = "NCBI Querier", 
                        instructions = "You are the PubMed querier. You take the user's input and use it to create a query to search PubMed Central for relevant papers.",
                        constraints = constraints,
                        register_default_events = True,
                        model = LLM_MODEL,)

    pmc_query = await ncbi_querier.aask([f"Take the following user request and use it construct a query to search PubMed Central for relevant papers. Limit your search to ONLY open access papers", user_request], PMCQuery)
    
    loader = PubmedReader()
    documents = loader.load_data(search_query = pmc_query.query)
    Settings.llm = OpenAI(model = LLM_MODEL)
    Settings.embed_model = OpenAIEmbedding(model = EMBEDDING_MODEL)
    index = VectorStoreIndex.from_documents(documents)
    query_engine = CitationQueryEngine.from_args(
        index,
        similarity_top_k = SIMILARITY_TOP_K,
        citation_chunk_size = CITATION_CHUNK_SIZE,
    )
    response = query_engine.query(f"""Given these papers, what are the possible open questions to investigate based on the users request? The user's request was:\n```{user_request}```""")
    study_suggester = Role(name = "Study Suggester", 
                        instructions = "You are the study suggester. You suggest a study to test a new hypothesis based on the cutting-edge information from the literature review.",
                        constraints = constraints,
                        register_default_events = True,
                        model = LLM_MODEL,)
    response_str = f"""The user's original request was:\n```{user_request}```\nA review of the literature yielded the following suggestions:\n```{response.response}```\nAnd the citations refer to the following papers:"""
    for i_node, node in enumerate(response.source_nodes):
        response_str += f"\n[{i_node + 1}] - {node.metadata['URL']}"

    suggested_study = await study_suggester.aask([f"Based on the results from the literature review, suggest a study to test a new hypothesis relevant to the user's request", response_str], SuggestedStudy)


    diagrammer = Role(name = "Diagrammer",
                        instructions = "You are the diagrammer. You create a diagram illustrating the workflow for the suggested study.",
                        constraints = None,
                        register_default_events = True,
                        model = LLM_MODEL,)
    study_diagram = await diagrammer.aask([f"Create a diagram illustrating the workflow for the suggested study:\n`{suggested_study.experiment_name}`", suggested_study], StudyDiagram)
    study_with_diagram = StudyWithDiagram(suggested_study = suggested_study, study_diagram = study_diagram)
    website_writer = Role(name = "Website Writer",
                            instructions = "You are the website writer. You create a single-page website summarizing the information in the suggested studies appropriately including the diagrams.",
                            constraints = None,
                            register_default_events = True,
                            model = LLM_MODEL,)

    summary_website = await website_writer.aask([f"Create a single-page website summarizing the information in the suggested study appropriately including the diagrams", study_with_diagram],
                                                SummaryWebsite)

    output_html = os.path.join(project_folder, 'suggested_study.html')
    suggested_study_json = os.path.join(project_folder, 'suggested_study.json')
    for d in [os.path.dirname(output_html)]:
        if not os.path.exists(d):
            os.makedirs(d)
    with open(output_html, 'w') as f:
        f.write(summary_website.html_code)
    with open(suggested_study_json, 'w') as f:
        json.dump(suggested_study.dict(), f, indent = 4)
    return {
        "suggested_study_json": suggested_study_json,
        "suggested_study": suggested_study.dict()
    }

async def main():
    parser = argparse.ArgumentParser(description='Run the study suggester pipeline')
    parser.add_argument('--project_name', type = str, default = 'test', help = 'The name of the project, used to create a folder to store the output files')
    parser.add_argument('--user_request', type=str, help='The user request to create a study around', required = True)
    parser.add_argument('--constraints', type=str, help='The user request to create a study around', default="")
    args = parser.parse_args()
    # await run_study_suggester(user_request = args.user_request, project_name = 'test')
    await run_study_suggester(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)