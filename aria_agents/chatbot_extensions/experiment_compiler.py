import dotenv
dotenv.load_dotenv()
import os
from typing import List, Optional, Union, Type, Any, get_type_hints, Tuple, Literal, Dict, Any
from typing_extensions import Self
import asyncio
import pickle as pkl
from schema_agents import schema_tool, Role
import json
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Union
import argparse
from typing import Union, List, Dict
import copy
from typing import Callable
from aria_agents.chatbot_extensions.aux import (
    SuggestedStudy,
    PMCQuery,
    create_pubmed_corpus,
    create_query_function,
    SummaryWebsite,
)
from tqdm.auto import tqdm

MAX_REVISIONS = 3

class ProtocolSection(BaseModel):
    """A section of an experimental protocol encompassing a specific set of steps falling under a coherent theme. The steps should be taken from existing protocols"""
    section_name : str = Field(..., description="The name of the section")
    steps : List[str] = Field(..., description="A list of steps that must be followed in order to carry out the experiment.")
    references : List[str] = Field(..., description="A list of references to existing protocols that the steps were taken from. These references should be in the form of URLs to the original protocol.")

class ExperimentalProtocol(BaseModel):
    """A detailed list of steps outlining an experimental procedure that to be carried out in the lab. The steps MUST be detailed enough for a new student to follow them exactly without any questions or doubts.
Do not include any data analysis portion of the study, only the procedure through the point of data collection. That means no statistical tests or data processing should be included unless they are necessary for downstream data collection steps."""
    # steps : List[str] = Field(..., description="A list of steps that must be followed in order to carry out the experiment. This string MUST be in markdown format and should contain no irregular characters.")
    sections : List[ProtocolSection] = Field(..., description="A list of sections that must be followed in order to carry out the experiment.")
    queries : List[str] = Field(..., description="A list of queries that were previously used to search for the protocol steps in the paper corpus. Do not repeat queries across protocol revisions.")

class ProtocolFeedback(BaseModel):
    """The expert scientist's feedback on a protocol"""
    complete : bool = Field(..., description="Whether the protocol is specified in enough detail for a new student to follow it exactly without any questions or doubts")
    feedback : str = Field(..., description="The expert scientist's feedback on the protocol")
    previous_feedback : List[str] = Field(..., description="The previous feedback given to the protocol writer that has already been addressed.")

async def get_protocol_feedback(protocol : ExperimentalProtocol, protocol_manager : Role, existing_feedback : ProtocolFeedback = None) -> ProtocolFeedback:
    if existing_feedback is None:
        pf = ProtocolFeedback(complete = False, feedback = "", previous_feedback = [])
    else:
        pf = existing_feedback
    res = await protocol_manager.aask(["""Is the following protocol specified in enough detail for a new student to follow it exactly without any questions or doubts? If not, say why.
                                       First you will be given the previous feedback you wrote for this protocol then you will be given the current version of the protocol.
                                       If the previous feedback is non-empty, do not give redundant feedback, give new feedback that will help the protocol writer improve the protocol further and make sure to save the previous feedback into the `previous_feedback` field""", 
                                       pf, protocol], output_schema=ProtocolFeedback)
    return res


QUERY_TOOL_TIP = """Queries MUST not be of the form of a question, but rather in the form of the expected protocol chunk you are looking for because this will find closely matching sentences to your desired information.

# EXAMPLE QUERIES: 
- `CHO cells were cultured for 20 minutes`
- `supernatent was aspirated and cells were washed with PBS`
- `cells were lysed with RIPA buffer`
- `sample was centrifuged at 1000g for 5 minutes`
- `All tissue samples were pulverized using a ball mill (MM400, Retsch) with precooled beakers and stainless-steel balls for 30 s at the highest frequency (30 Hz)`
- `pulverized and frozen samples were extracted using the indicated solvents and subsequent steps of the respective protocol`
- `After a final centrifugation step the solvent extract of the protocols 100IPA, IPA/ACN and MeOH/ACN were transferred into a new 1.5 ml tube (Eppendorf) and snap-frozen until kit preparation.` 
- `The remaining protocols were dried using an Eppendorf Concentrator Plus set to no heat, stored at −80°C and reconstituted in 60 µL isopropanol (30 µL of 100% isopropanol, followed by 30 µL of 30% isopropanol in water) before the measurement.`"""


class CorpusQueries(BaseModel):
    """A list of queries to search against a given corpus of protocols"""
    queries : List[str] = Field(..., description=f"A list of queries to search against a given corpus of protocols. {QUERY_TOOL_TIP}")

class CorpusQueriesResponses(BaseModel):
    """A list of responses to queries made against a corpus of protocols"""
    responses : Dict[str, str] = Field(..., description="A dictionary of responses to queries made against a corpus of protocols")


async def write_protocol(protocol : Union[ExperimentalProtocol, SuggestedStudy], feedback : ProtocolFeedback, query_function : Callable, role : Role) -> ExperimentalProtocol:
    if isinstance(protocol, SuggestedStudy):
        prompt = f"""Take the following suggested study and use it to produce a detailed protocol telling a student exactly what steps they should follow in the lab to collect data. Do not include any data analysis or conclusion-drawing steps, only data collection."""
        messages = [prompt, protocol]
        protocol_updated = await role.aask(messages, output_schema=ExperimentalProtocol)
    else:
        prompt = f"""You are being given a laboratory protocol that you have written and the feedback to make the protocol clearer for the lab worker who will execute it. First the protocol will be provided, then the feedback."""
        messages = [prompt, protocol, feedback]
        query_messages = [x for x in messages] + ["Use the feedback to produce a list of queries that you will use to search a given corpus of existing protocols for reference to existing steps in these protocols. Note the previous feedback and queries that you have already tried, and do not repeat them. Rather come up with new queries that will address the new feedback and improve the protocol further."]
        queries = await role.aask(query_messages, output_schema=CorpusQueries)
        queries_responses = CorpusQueriesResponses(responses = {
            query : await query_function(query) for query in queries.queries
        })
        protocol_messages = [x for x in messages] + [f"You searched a corpus of existing protocols for relevant steps in existing protocols and found the following responses",
                                                     queries_responses,
                                                     f"Use these protocol corpus query responses to update and revise your protocol according to the feedback. Save the queries you used into the running list of previous queries. If a given query did not return a response from the corpus, do your best to update the protocol without the information from that single query using your internal knowledge or sources like protocols.io"]
        protocol_updated = await role.aask(protocol_messages, output_schema=ExperimentalProtocol)
    return protocol_updated


project_folders = os.environ.get('PROJECT_FOLDERS', './projects')
os.makedirs(project_folders, exist_ok = True)


PAPER_LIMIT = 20
LLM_MODEL = 'gpt-4o'
EMBEDDING_MODEL = "text-embedding-3-small"
SIMILARITY_TOP_K = 8
CITATION_CHUNK_SIZE = 1024
project_folders = os.environ.get('PROJECT_FOLDERS', './projects')
os.makedirs(project_folders, exist_ok = True)



@schema_tool
async def run_experiment_compiler(
    project_name: str = Field(description = "The name of the project, used to create a folder to store the output files and to read input files from the study suggester run"),
    constraints: str = Field("", description = "Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc."),
    max_revisions: int = Field(MAX_REVISIONS, description = "The maximum number of protocol revision rounds to allow")
):
    """Generate an investigation from a suggested study"""
    project_folder = os.path.join(project_folders, project_name)
    os.makedirs(project_folder, exist_ok = True)
    
    protocol_writer = Role(name="Protocol Writer",
                    instructions="""You are an extremely detail oriented student who works in a biological laboratory. You read protocols and revise them to be specific enough until you and your fellow students could execute the protocol yourself in the lab.
    You do not conduct any data analysis, only data collection so your protocols only include steps up through the point of collecting data, not drawing conclusions.""",
                    constraints=constraints,
                    register_default_events=True,
                    model=LLM_MODEL)

    protocol_manager = Role(name="Protocol manager",
                        instructions="You are an expert laboratory scientist. You read protocols and manage them to ensure that they are clear and detailed enough for a new student to follow them exactly without any questions or doubts.",
                        constraints=constraints,
                        register_default_events=True,
                        model=LLM_MODEL)

    suggested_study_json = os.path.join(project_folder, "suggested_study.json")
    suggested_study = SuggestedStudy(**json.loads(open(suggested_study_json).read()))

    pmc_query = await protocol_writer.aask([f"Read the following suggested study and use it construct a query to search PubMed Central for relevant protocols that you will use to construct steps. Limit your search to ONLY open access papers", suggested_study], PMCQuery)
    query_engine = await create_pubmed_corpus(pmc_query)
    query_function = create_query_function(query_engine)
    

    protocol = await write_protocol(protocol = suggested_study,
                                    feedback = None,
                                    query_function = query_function,
                                    role = protocol_writer)

    protocol_feedback = await get_protocol_feedback(protocol, protocol_manager)
    revisions = 0
    pbar = tqdm(total=max_revisions)
    while not protocol_feedback.complete and revisions < max_revisions:
        protocol = await write_protocol(protocol = protocol,
                                        feedback = protocol_feedback,
                                        query_function = query_function,
                                        role = protocol_writer)
        protocol_feedback = await get_protocol_feedback(protocol, protocol_manager, protocol_feedback)
        revisions += 1
        pbar.update(1)
    pbar.close()

    website_writer = Role(name = "Website Writer",
                            instructions = "You are the website writer. You create a single-page website summarizing the information in the experimental protocol appropriately including any diagrams.",
                            constraints = None,
                            register_default_events = True,
                            model = LLM_MODEL,)

    summary_website = await website_writer.aask([f"Create a single-page website summarizing experimental protocol appropriately including any diagrams and references", protocol],
                                                SummaryWebsite)


    protocol_json = os.path.join(project_folder, "protocol.json")
    output_html = os.path.join(project_folder, 'protocol.html')
    with open(output_html, 'w') as f:
        f.write(summary_website.html_code)
    with open(protocol_json, 'w') as f:
        json.dump(protocol.dict(), f, indent = 4)
    return {
        "protocol": protocol.dict(),
    }

async def main():
    parser = argparse.ArgumentParser(description='Generate an investigation')
    parser.add_argument('--project_name', type = str, help = 'The name of the project', required = True)
    parser.add_argument('--max_revisions', type = int, help = 'The maximum number of protocol agent revisions to allow', default = MAX_REVISIONS)
    parser.add_argument('--constraints', type=str, help='Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.', default="")
    args = parser.parse_args()
    await run_experiment_compiler(**vars(args))




if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)