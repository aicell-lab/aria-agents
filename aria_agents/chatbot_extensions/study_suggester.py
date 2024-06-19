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
from aria_agents.chatbot_extensions.aux import (
    SuggestedStudy,
    PMCQuery,
    create_pubmed_corpus,
    create_query_function,
    SummaryWebsite
)

import os


class StudyDiagram(BaseModel):
    """A diagram written in mermaid.js showing what the expected data from a study will look like"""
    diagram_code : str = Field(description = "The code for a mermaid.js diagram (either a XYChart, Pie, or QuadrantChart) showing what the expected data results would look like for the experiment")

class StudyWithDiagram(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge information from the literature review"""
    suggested_study : SuggestedStudy = Field(description = "The suggested study to test a new hypothesis")
    study_diagram : StudyDiagram = Field(description = "The diagram illustrating the workflow for the suggested study")



PAPER_LIMIT = 20
LLM_MODEL = 'gpt-4o'
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_TOP_K = 5
CITATION_CHUNK_SIZE = 1024
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
    
    study_suggester = Role(name = "Study Suggester", 
                        instructions = "You are the study suggester. You suggest a study to test a new hypothesis based on the cutting-edge information from the literature review.",
                        constraints = constraints,
                        register_default_events = True,
                        model = LLM_MODEL,)

    pmc_query = await ncbi_querier.aask([f"Take the following user request and use it construct a query to search PubMed Central for relevant papers. Limit your search to ONLY open access papers", user_request], PMCQuery)
    query_engine = await create_pubmed_corpus(pmc_query)
    query_function = create_query_function(query_engine)
    suggested_study = await study_suggester.acall([f"Design a study to address an open question in the field based on the following user request: ```{user_request}```",
                                                  "You have access to an already-collected corpus of PubMed papers and the ability to query it. If you don't get good information from your query, try again with a different query. You can get more results from maker your query more generic or more broad. Keep going until you have a good answer. You should try at the very least 5 different queries"],
                                                  tools = [query_function],
                                                  output_schema = SuggestedStudy)


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
    parser.add_argument('--constraints', type=str, help='Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.', default="")
    args = parser.parse_args()
    # await run_study_suggester(user_request = args.user_request, project_name = 'test')
    await run_study_suggester(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)