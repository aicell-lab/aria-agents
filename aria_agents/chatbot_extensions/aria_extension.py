from aria_agents.utils import ChatbotExtension
from aria_agents.chatbot_extensions.study_suggester import run_study_suggester
from aria_agents.chatbot_extensions.experiment_compiler import run_experiment_compiler
# from aria_agents.chatbot_extensions.analyzers import run_analyzers

def get_extension():
    return ChatbotExtension(
        id="aria",
        name="Aria",
        description="Utility tools for suggesting studies, compiling experiments, and analyzing data.",
        tools=dict(
            study_suggester=run_study_suggester,
            experiment_compiler=run_experiment_compiler,
            # data_analyst=run_analyzers,
        )
    )


if __name__ == "__main__":
    import asyncio
    async def main():
        extension = get_extension()
        print(await extension.tools["study_suggester"](user_request="I'm interested in designing a study about the metabolomics of U2OS cells", project_name="test-project"))

    # Run the async function
    asyncio.run(main())
