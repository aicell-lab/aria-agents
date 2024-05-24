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
from aux_classes import SuggestedStudy
from aux_tools import *

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
    html_code: str = Field(description = "The html code for a single page website summarizing the information in the suggested studies appropriately including the diagrams. Make sure to include the original user request as well.")

    

CONCURENCY_LIMIT = 3
PAPER_LIMIT = 5
LLM_MODEL = 'gpt-4o'
project_folders = os.environ.get('PROJECT_FOLDERS', './projects')
os.makedirs(project_folders, exist_ok = True)

@schema_tool
async def run_study_suggester(
    user_request: str = Field(description = "The user's request to create a study around, framed in terms of a scientific question"),
    project_name: str = Field(description = "The name of the project, used to create a folder to store the output files"),
):
    """Create a study suggestion based on the user's request. This includes a literature review, a suggested study, a diagram of the study, and a summary website."""
    os.makedirs(os.path.join(project_folders, project_name), exist_ok = True)
    ncbi_querier = Role(name = "NCBI Querier", 
                        instructions = "You are the PubMed querier. You query the PubMed Central database for papers relevant to the user's input. You also scrape the abstracts and other relevant information from the papers.",
                        constraints = None,
                        register_default_events = True,
                        model = LLM_MODEL,)
    structured_user_input = await ncbi_querier.aask(user_request, StructuredUserInput)
    structured_query = await ncbi_querier.aask([
        f"Take this user's stated interest and use it to search PubMed Central for relevant papers. These papers will be used to figure out the state of the art of relevant to the user's interests. Ultimately this will be used to design new hypotheses and studies. Limit the search to return at most {PAPER_LIMIT} paper IDs.", 
        structured_user_input],
        StructuredQuery)
    search_results = await pmc_search(ncbi_query_url = structured_query.query_url)
    pmc_ids = re.findall(r'<Id>(\d+)</Id>', search_results)
    paper_contents = []
    for pmc_id in tqdm(pmc_ids):
        paper_contents.append(await pmc_efetch(pmc_ids = [pmc_id]))
        # time.sleep(0.3)
        asyncio.sleep(0.3)
    paper_bodies = [x if len(x) > 0 else None for x in [re.findall(r'<body>.*</body>', p, flags = re.DOTALL) for p in paper_contents]]
    paper_summaries = []
    semaphore = asyncio.Semaphore(CONCURENCY_LIMIT)
    tasks = [process_paper(pb, pmc_ids[i], user_request, semaphore)
                for i, pb in enumerate(paper_bodies) if pb is not None]

    paper_summaries = await asyncio.gather(*tasks)
    literature_review = LiteratureReview(paper_summaries = paper_summaries)
    study_suggester = Role(name = "Study Suggester", 
                        instructions = "You are the study suggester. You suggest a study to test a new hypothesis based on the cutting-edge information from the literature review.",
                        constraints = None,
                        register_default_events = True,
                        model = 'gpt-4o',)
    suggested_study = await study_suggester.aask([f"Based on the cutting-edge information from the literature review, suggest a study to test a new hypothesis relevant to the user's request:\n`{user_request}`", literature_review], 
                                                 SuggestedStudy)
    diagrammer = Role(name = "Diagrammer",
                        instructions = "You are the diagrammer. You create a diagram illustrating the workflow for the suggested study.",
                        constraints = None,
                        register_default_events = True,
                        model = 'gpt-4-turbo-preview',)
    study_diagram = await diagrammer.aask([f"Create a diagram illustrating the workflow for the suggested study:\n`{suggested_study.experiment_name}`", suggested_study], StudyDiagram)
    study_with_diagram = StudyWithDiagram(suggested_study = suggested_study, study_diagram = study_diagram)
    website_writer = Role(name = "Website Writer",
                            instructions = "You are the website writer. You create a single-page website summarizing the information in the suggested studies appropriately including the diagrams.",
                            constraints = None,
                            register_default_events = True,
                            model = 'gpt-4-turbo-preview',)

    summary_website = await website_writer.aask([f"Create a single-page website summarizing the information in the suggested study appropriately including the diagrams", study_with_diagram],
                                                SummaryWebsite)

    output_html = os.path.join(project_folders, project_name, 'output.html')
    suggested_study_json = os.path.join(project_folders, project_name, 'suggested_study.json')
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
    parser.add_argument('--user_request', type=str, help='The user request to create a study around', required = True)
    parser.add_argument('--concurrency_limit', type=int,  default = 3, help='The number of concurrent requests to make to the NCBI API')
    parser.add_argument('--paper_limit', type=int, default = 5, help='The maximum number of paper to fetch from PubMed Central')
    parser.add_argument('--output_html', type = str, default = 'output.html', help = 'The path to save the output html')
    parser.add_argument('--suggested_study_json', type = str, default = 'suggested_study.json', help = 'The path to save the suggested study')
    args = parser.parse_args()
    await run_study_suggester(user_request = args.user_request, project_name = 'test')

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
    # loop = asyncio.get_event_loop()
    # loop.create_task(main())
    # loop.run_forever()