import pytest
from aria_agents.chatbot_extensions.aux import check_pmc_query_hits, create_corpus_function, PMCQuery

@pytest.fixture(scope="module")
def pmc_query():
    return PMCQuery(query='"osmotic stress"[Title/Abstract] AND "yeast cells"[Title/Abstract]')

@pytest.mark.asyncio
async def test_check_pmc_query_hits(pmc_query):
    result = await check_pmc_query_hits(pmc_query=pmc_query)
    assert isinstance(result, str)
    n_hits = int(result.split()[-2])
    assert result == f"The query `{pmc_query.query}` returned {n_hits} hits."
    assert n_hits >= 0

@pytest.mark.asyncio
async def test_create_corpus_function(artifact_manager, config, pmc_query):
    corpus_function = create_corpus_function(artifact_manager, config)
    result = await corpus_function(pmc_query=pmc_query)
    assert isinstance(result, str)
    n_docs = int(result.split()[3])
    assert result == f"Pubmed corpus with {n_docs} papers has been created."
    assert n_docs > 0
