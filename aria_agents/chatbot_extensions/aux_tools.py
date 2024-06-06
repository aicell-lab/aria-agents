import asyncio
import aiohttp
from pydantic import Field
from schema_agents import schema_tool
from typing import List

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