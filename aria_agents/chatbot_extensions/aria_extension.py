from aria_agents.utils import ChatbotExtension
from aria_agents.hypha_store import HyphaDataStore
from aria_agents.chatbot_extensions.study_suggester import create_study_suggester_function
from aria_agents.chatbot_extensions.experiment_compiler import create_experiment_compiler_function
# from aria_agents.chatbot_extensions.analyzers import create_analyzers_function

def get_extension(ds: HyphaDataStore = None):
    return ChatbotExtension(
        id="aria",
        name="Aria",
        description="Utility tools for suggesting studies, compiling experiments, and analyzing data.",
        tools=dict(
            study_suggester=create_study_suggester_function(ds),
            experiment_compiler=create_experiment_compiler_function(ds),
            # data_analyst=create_analyzers_function(ds),
        )
    )


if __name__ == "__main__":
    import asyncio

    async def main():
        extension = get_extension()
        print(await extension.tools["study_suggester"](user_request="I'm interested in designing a study about the metabolomics of U2OS cells", project_name="test-project"))

    # Run the async function
    asyncio.run(main())
