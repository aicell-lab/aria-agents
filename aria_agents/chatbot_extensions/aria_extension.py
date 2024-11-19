from aria_agents.chatbot_extensions.experiment_compiler import (
    create_experiment_compiler_function,
)
from aria_agents.chatbot_extensions.study_suggester import (
    create_study_suggester_function,
)
from aria_agents.artifact_manager import ArtifactManager
from aria_agents.utils import ChatbotExtension


def get_extension(artifact_manager: ArtifactManager = None) -> ChatbotExtension:
    return ChatbotExtension(
        id="aria",
        name="Aria",
        description=(
            "Utility tools for suggesting studies, compiling experiments, and"
            " analyzing data."
        ),
        tools=dict(
            study_suggester=create_study_suggester_function(artifact_manager),
            experiment_compiler=create_experiment_compiler_function(artifact_manager),
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
