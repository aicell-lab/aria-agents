from aria_agents.chatbot_extensions.experiment_compiler import (
    create_experiment_compiler_function,
)
from aria_agents.chatbot_extensions.study_suggester import (
    create_study_suggester_function, create_pubmed_query_function, create_summary_website_function, create_create_diagram_function
)
from aria_agents.chatbot_extensions.analyzers import (
    create_explore_data
)
from aria_agents.artifact_manager import ArtifactManager
from aria_agents.utils import load_config, ChatbotExtension

def get_extension(artifact_manager: ArtifactManager = None) -> ChatbotExtension:
    event_bus = artifact_manager.get_event_bus() if artifact_manager else None
    config = load_config()
    llm_model = config["llm_model"]
    
    return ChatbotExtension(
        id="aria",
        name="Aria",
        description=(
            "Utility tools for suggesting studies, compiling experiments, and"
            " analyzing data."
        ),
        tools=dict(
            study_suggester=create_study_suggester_function(artifact_manager, llm_model),
            experiment_compiler=create_experiment_compiler_function(artifact_manager),
            data_analyzer = create_explore_data(artifact_manager),
            query_pubmed = create_pubmed_query_function(artifact_manager, llm_model),
            run_study_with_diagram = create_create_diagram_function(event_bus, llm_model),
            create_summary_website = create_summary_website_function(artifact_manager)
        ),
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
