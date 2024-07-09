import os

import dotenv
from schema_agents import schema_tool

from aria_agents.hypha_store import HyphaDataStore

dotenv.load_dotenv()
import argparse
import asyncio
import json
import os

import dotenv
from pydantic import BaseModel, Field
from schema_agents import Role, schema_tool

from aria_agents.chatbot_extensions.aux import (PMCQuery, SuggestedStudy,
                                                SummaryWebsite,
                                                create_pubmed_corpus,
                                                create_query_function)
from aria_agents.hypha_store import HyphaDataStore


PAPER_LIMIT = 20
LLM_MODEL = 'gpt-4o'
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_TOP_K = 5
CITATION_CHUNK_SIZE = 1024
project_folders = os.environ.get('PROJECT_FOLDERS', './projects')
os.makedirs(project_folders, exist_ok = True)


class StudyDiagram(BaseModel):
    """A diagram written in mermaid.js showing what the expected data from a study will look like"""
    diagram_code : str = Field(description = "The code for a mermaid.js diagram (either a XYChart, Pie, or QuadrantChart) showing what the expected data results would look like for the experiment")

class StudyWithDiagram(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge information from the literature review"""
    suggested_study : SuggestedStudy = Field(description = "The suggested study to test a new hypothesis")
    study_diagram : StudyDiagram = Field(description = "The diagram illustrating the workflow for the suggested study")


def create_study_suggester_function(ds: HyphaDataStore = None):
    @schema_tool
    async def run_study_suggester(
        user_request: str = Field(description = "The user's request to create a study around, framed in terms of a scientific question"),
        project_name: str = Field(description = "The name of the project, used to create a folder to store the output files"),
        constraints: str = Field("", description = "Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc."),
    ):
        """Create a study suggestion based on the user's request. This includes a literature review, a suggested study, and a summary website."""
        if ds is None:
            project_folder = os.path.abspath(os.path.join(project_folders, project_name))
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

        if ds is None:
            # Save the suggested study to a JSON file
            suggested_study_file = os.path.join(project_folder, "suggested_study.json")
            with open(suggested_study_file, "w") as f:
                json.dump(suggested_study.dict(), f, indent=4)
            suggested_study_url = "file://" + suggested_study_file

            # Save the summary website to a HTML file
            summary_website_file = os.path.join(project_folder, "suggested_study.html")
            with open(summary_website_file, "w") as f:
                f.write(summary_website.html_code)
            summary_website_url = "file://" + summary_website_file
        else:
            # Save the suggested study to the HyphaDataStore
            suggested_study_id = ds.put(
                obj_type="json",
                value=suggested_study.dict(),
                name=f"{project_name}:suggested_study.json",
            )
            suggested_study_url = ds.get_url(suggested_study_id)

            # Save the summary website to the HyphaDataStore
            summary_website_id = ds.put(
                obj_type="file",
                value=summary_website.html_code,
                name=f"{project_name}:suggested_study.html",
            )
            summary_website_url = ds.get_url(summary_website_id)

        return {
            "summary_website_url": summary_website_url,
            "suggested_study_url": suggested_study_url,
            "suggested_study": suggested_study.dict(),
        }
    return run_study_suggester


async def main():
    parser = argparse.ArgumentParser(description='Run the study suggester pipeline')
    parser.add_argument('--user_request', type=str, help='The user request to create a study around', required = True)
    parser.add_argument('--project_name', type = str, help = 'The name of the project, used to create a folder to store the output files',  default = 'test')
    parser.add_argument('--constraints', type=str, help='Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.', default="")
    args = parser.parse_args()

    # from imjoy_rpc.hypha import connect_to_server
    # server = await connect_to_server({"server_url": "https://ai.imjoy.io"})
    # ds = HyphaDataStore()
    # await ds.setup(server)
    ds = None

    run_study_suggester = create_study_suggester_function(ds)
    await run_study_suggester(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
