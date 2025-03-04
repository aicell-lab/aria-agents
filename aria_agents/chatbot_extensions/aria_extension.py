from aria_agents.chatbot_extensions.experiment_compiler import (
    create_experiment_compiler_function,
)
from aria_agents.chatbot_extensions.study_suggester import (
    create_study_suggester_function, create_summary_website_function, create_create_diagram_function
)
from aria_agents.chatbot_extensions.analyzers import (
    create_explore_data
)
from aria_agents.utils import load_config, ChatbotExtension
from typing import Optional
from schema_agents.utils.common import EventBus

def get_extension(event_bus: Optional[EventBus] = None) -> ChatbotExtension:
    config = load_config()
    llm_model = config["llm_model"]
    
    return ChatbotExtension(
        id="aria",
        name="Aria",
        description=(
            "Utility tools for suggesting studies, compiling experiments, and"
            " analyzing data."
        ),
        tools={
            "study_suggester": create_study_suggester_function(config),
            "experiment_compiler": create_experiment_compiler_function(config),
            "data_analyzer": create_explore_data(llm_model, event_bus),
            "run_study_with_diagram": create_create_diagram_function(llm_model, event_bus),
            "create_summary_website": create_summary_website_function(llm_model, event_bus)
        },
    )

if __name__ == "__main__":
    import asyncio

    async def main():
        extension = get_extension()
        print(
            await extension.tools["study_suggester"](
                user_request=(
                    "I'm interested in designing a study about the metabolomics"
                    " of U2OS cells"
                ),
                constraints="",
            )
        )

    # Run the async function
    asyncio.run(main())
