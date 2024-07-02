import pytest
import os
if "OPENAI_API_KEY" not in os.environ:
    import dotenv
    dotenv.load_dotenv()
from aria_agents.chatbot_extensions.aria_extension import run_study_suggester
from aria_agents.chatbot_extensions.experiment_compiler import run_experiment_compiler

@pytest.mark.asyncio
async def test_suggestion_and_experiment():
    user_request = "I'm interested in studying the metabolomics of U2OS cells"
    project_name = "metabolomics_study"
    constraints = "The only analytical equipment I have access to is an orbitrap mass spectrometer"

    study_suggester_res = await run_study_suggester(
        user_request = user_request,
        project_name = project_name,
        constraints = constraints,
    )

    experiment_compiler_res = run_experiment_compiler(
        project_name=project_name,
        constraints=constraints,
    )
