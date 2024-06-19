import asyncio
import aiohttp
from pydantic import Field
from schema_agents import schema_tool
from typing import List

async def call_api(url: str, delay : float = 0.4) -> bytes:
    url = url.replace(' ', '+') 
    await asyncio.sleep(delay)  # Delay call to avoid hitting API rate limits
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                response.raise_for_status() 
                return await response.read()
        except aiohttp.ClientError as e:
            print(f"Failed to fetch data from {url}: {e}")
            raise e

@schema_tool
async def pmc_search(ncbi_query_url : str = Field(description = "The NCBI API web url to use for this query.")) -> str:
    """Uses the NCBI web API to search the PubMed Central (pmc) database."""
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