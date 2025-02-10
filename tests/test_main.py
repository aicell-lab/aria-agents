import pytest
import os
import asyncio
from aria_agents.chatbot_extensions.study_suggester import create_study_suggester_function
from aria_agents.chatbot_extensions.experiment_compiler import create_experiment_compiler_function
if "OPENAI_API_KEY" not in os.environ:
    import dotenv
    dotenv.load_dotenv()

@pytest.mark.asyncio
async def test_suggestion_and_experiment():
    user_request = "I'm interested in studying the metabolomics of U2OS cells"
    constraints = "The only analytical equipment I have access to is an orbitrap mass spectrometer"

    run_study_suggester = create_study_suggester_function()
    run_experiment_compiler = create_experiment_compiler_function()

    study_suggester_res = await run_study_suggester(
        user_request = user_request,
        constraints = constraints,
    )

    experiment_compiler_res = run_experiment_compiler(
        constraints=constraints,
    )

    print(study_suggester_res)
    print(experiment_compiler_res)

if __name__ == "__main__":
    asyncio.run(test_suggestion_and_experiment())
