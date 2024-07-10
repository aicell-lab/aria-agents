from schema_agents.utils.common import EventBus

from aria_agents.chatbot_extensions.experiment_compiler import (
    create_experiment_compiler_function,
)
from aria_agents.chatbot_extensions.study_suggester import (
    create_study_suggester_function,
)
from aria_agents.hypha_store import HyphaDataStore
from aria_agents.utils import ChatbotExtension

# from aria_agents.chatbot_extensions.analyzers import create_analyzers_function


def get_extension(data_store: HyphaDataStore = None, chat_event_bus: EventBus = None):
    return ChatbotExtension(
        id="aria",
        name="Aria",
        description="Utility tools for suggesting studies, compiling experiments, and analyzing data.",
        tools=dict(
            study_suggester=create_study_suggester_function(data_store, chat_event_bus),
            experiment_compiler=create_experiment_compiler_function(data_store, chat_event_bus),
            # data_analyst=create_analyzers_function(data_store),
        ),
    )


if __name__ == "__main__":
    import asyncio

    async def main():
        extension = get_extension()
        print(
            await extension.tools["study_suggester"](
                user_request="I'm interested in designing a study about the metabolomics of U2OS cells",
                project_name="test",
                constraints="",
            )
        )
        print(
            await extension.tools["experiment_compiler"](
                project_name="test", max_revisions=3, constraints=""
            )
        )

    # Run the async function
    asyncio.run(main())
