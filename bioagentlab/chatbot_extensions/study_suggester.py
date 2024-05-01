import aiohttp
from schema_agents import schema_tool
import time
from tqdm.auto import tqdm
import argparse

class PapersSummary(BaseModel):
    """A summary of the papers found in the PubMed Central database search"""
    state_of_field : str = Field(description="A summary of the current state of the field")
    open_questions : str = Field(description="A summary of the open questions in the field")

async def call_api(url: str) -> bytes:
    url = url.replace(' ', '+') 
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status() 
                return await response.read()
        except aiohttp.ClientError as e:
            print(f"Failed to fetch data from {url}: {e}")
            raise e

@schema_tool
async def pmc_search(ncbi_query_url : str = Field(description = "The NCBI API web url to use for this query")) -> str:
    """Uses the NCBI web API to search the PubMed Central (pmc) database"""
    query_response = await call_api(ncbi_query_url)
    query_response = query_response.decode()
    return query_response

@schema_tool
async def pmc_efetch(pmc_ids: List[str] = Field(description="The PubMed Central IDs of the articles")) -> str:
    """Uses the NCBI Eutils API's efetch functionality to get in-depth information about a set of papers in the PubMed Central database given their IDs"""
    pmc_ids = ",".join(pmc_ids)
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmc_ids}"
    query_response = await call_api(url)
    query_response = query_response.decode()
    return query_response

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
        # Assuming Role and aask are properly defined and awaitable
        r = Role(name=f"Paper Agent PMC ID {pmc_id}",
                 instructions=f"You are an agent assigned to study the paper (PMC ID {pmc_id}) provided to you in the context of the user's request (`{user_request}`)",
                 constraints=None,
                 register_default_events=True,
                 model='gpt-4-turbo-preview')
        return await r.aask([f"The user wants to design a cutting-edge scientific study based on the original request:\n`{user_request}`\nRead the following paper's contents and scrape it for information relevant to designing a study for the user",
                             f"Paper content:\n`{pb}`"], ContextualizedPaperSummary)
    
class LiteratureReview(BaseModel):
    """A collection of summaries from papers found to be relevant to the user's request"""
    paper_summaries : List[ContextualizedPaperSummary] = Field(description = """The summaries from the individual papers""")

class SuggestedStudy(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge"""
    user_request : str = Field(description = "The original user request")
    experiment_name : str = Field(description = "The name of the experiment")
    experiment_material : List[str] = Field(description = "The materials required for the experiment")
    experiment_expected_results : str = Field(description = "The expected results of the experiment")
    experiment_protocol : List[str] = Field(description = "The protocol steps for the experiment")
    experiment_hypothesis : str = Field(description = "The hypothesis to be tested by the experiment")

class StudyDiagram(BaseModel):
    """A diagram written in mermaid.js showing what the expected data from a study will look like"""
    diagram_code : str = Field(description = "The code for a mermaid.js diagram (either a XYChart, Pie, or QuadrantChart) showing what the expected data results would look like for the experiment")

class StudyWithDiagram(BaseModel):
    """A suggested study to test a new hypothesis relevant to the user's request based on the cutting-edge information from the literature review"""
    suggested_study : SuggestedStudy = Field(description = "The suggested study to test a new hypothesis")
    study_diagram : StudyDiagram = Field(description = "The diagram illustrating the workflow for the suggested study")

class SummaryWebsite(BaseModel):
    """A summary single-page webpage written in html that neatly presents the suggested study for user review"""
    html_code: str = Field(description = "The html code for a single page website summarizing the information in the suggested studies appropriately including the diagrams")


async def main():
    parser = argparse.ArgumentParser(description='Run the study suggester pipeline')
    parser.add_argument('--user_request', type=str, help='The user request to create a study around')
    parser.add_argument('--concurrency_limit', type=int, help='The number of concurrent requests to make to the NCBI API')
    args = parser.parse_args()


    ncbi_querier = Role(name = "NCBI Querier", 
                        instructions = "You are the PubMed querier. You query the PubMed Central database for papers relevant to the user's input. You also scrape the abstracts and other relevant information from the papers.",
                        constraints = None,
                        register_default_events = True,
                        model = 'gpt-4-turbo-preview',)
    structured_user_input = await ncbi_querier.aask(args.user_request, StructuredUserInput)
    structured_query = await ncbi_querier.aask([
        "Take this user's stated interest and use it to search PubMed Central for relevant papers. These papers will be used to figure out the state of the art of relevant to the user's interests. Ultimately this will be used to design new hypotheses and studies", 
        structured_user_input],
        StructuredQuery)
    search_results = await pmc_search(ncbi_query_url = structured_query.query_url)
    pmc_ids = re.findall(r'<Id>(\d+)</Id>', search_results)
    paper_contents = []
    for pmc_id in tqdm(pmc_ids):
        paper_contents.append(await pmc_efetch(pmc_ids = [pmc_id]))
        time.sleep(0.3)
    paper_bodies = [x if len(x) > 0 else None for x in [re.findall(r'<body>.*</body>', p, flags = re.DOTALL) for p in paper_contents]]
    paper_summaries = []
    semaphore = asyncio.Semaphore(args.concurrency_limit)
    tasks = [process_paper(pb, pmc_ids[i], args.user_request, semaphore)
                for i, pb in enumerate(paper_bodies) if pb is not None]

    paper_summaries = await asyncio.gather(*tasks)
    literature_review = LiteratureReview(paper_summaries = paper_summaries)
    study_suggester = Role(name = "Study Suggester", 
                        instructions = "You are the study suggester. You suggest a study to test a new hypothesis based on the cutting-edge information from the literature review.",
                        constraints = None,
                        register_default_events = True,
                        model = 'gpt-4-turbo-preview',)
    suggested_study = await study_suggester.aask([f"Based on the cutting-edge information from the literature review, suggest a study to test a new hypothesis relevant to the user's request:\n`{args.user_request}`", literature_review], SuggestedStudy)
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
    summary_website = await website_writer.aask([f"Create a single-page website summarizing the information in the suggested studies appropriately including the diagrams", study_with_diagram], SummaryWebsite)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()