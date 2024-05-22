from aria_agents.utils import ChatbotExtension
from aria_agents.chatbot_extensions.study_suggester import pmc_search, pmc_efetch


def get_extension():
    return ChatbotExtension(
        id="ncbi",
        name="NCBI",
        description="Utilize the NCBI web API to search and retrieve detailed information from the PubMed Central (PMC) database.",
        tools=dict(
            search=pmc_search,
            efetch=pmc_efetch,
        )
    )


if __name__ == "__main__":
    import asyncio
    async def main():
        extension = get_extension()
        print(await extension.tools["search"](ncbi_query_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pmc&term=COVID-19&retmax=5"))
        print(await extension.tools["efetch"](pmc_ids=["11108703"]))

    # Run the async function
    asyncio.run(main())