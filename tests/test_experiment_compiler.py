import pytest
from aria_agents.chatbot_extensions.experiment_compiler import (
    create_experiment_compiler_function,
    ExperimentalProtocol
)

@pytest.mark.slow
@pytest.mark.asyncio
async def test_run_experiment_compiler(config, suggested_study):
    experiment_compiler = create_experiment_compiler_function(config)
    result = await experiment_compiler(
        suggested_study=suggested_study,
        constraints="",
        max_revisions=2
    )

    assert result.status.type == "success"
    assert isinstance(result.response, ExperimentalProtocol)
    assert len(result.to_save) == 2
    assert any(f.name == "experimental_protocol.json" for f in result.to_save)
    assert any(f.name == "experimental_protocol.html" for f in result.to_save)
