import argparse
import os
import asyncio
import uuid
from io import StringIO
from typing import List, Callable, Dict
from pydantic import BaseModel, Field
import pandas as pd
from pandas.errors import EmptyDataError
from pandasai.llm import OpenAI as PaiOpenAI
from pandasai import Agent as PaiAgent
from schema_agents import schema_tool, Role
from schema_agents.utils.common import current_session, EventBus
from aria_agents.utils import get_project_folder, get_session_id, load_config, save_to_artifact_manager, ask_agent
from aria_agents.artifact_manager import AriaArtifacts

AGENT_MAX_RETRIES = 5

async def read_df(file_path: str, content: str = None) -> pd.DataFrame:
    def _read_file(path, content = None):
        ext = os.path.splitext(path)[1].lower()
        file_content = StringIO(content) if content else path
        try:
            match ext:
                case ".csv":
                    return pd.read_csv(file_content)
                case ".tsv":
                    return pd.read_csv(file_content, sep='\t')
                case ".xlsx":
                    return pd.read_excel(file_content, engine='openpyxl')
                case _:
                    return pd.read_csv(file_content, sep=None, engine='python')
        except EmptyDataError:
            print(f"Warning: The file {path} is empty or contains no data.")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error reading file {path}: {str(e)}")
            raise ValueError(f"Unable to open file {path} as tabular file: {str(e)}") from e

    return await asyncio.get_event_loop().run_in_executor(None, _read_file, file_path, content)

class PlotPaths(BaseModel):
    """A list of file paths to the plots (or any .png files) created by the data analysis bot"""
    plot_paths: List[str] = Field(description="A list of paths to the .png files created by the data analysis bot")
    plot_meanings: List[str] = Field(description="A list of meanings of the plots, why they were created and what they show")


async def upload_plots(plot_paths: PlotPaths, artifact_manager: AriaArtifacts) -> Dict[str, str]:
    if artifact_manager is None:
        return plot_paths.plot_paths
    
    plot_urls = {}
    for plot_path in plot_paths.plot_paths:
        with open(plot_path, "rb") as image_file:
            plot_content = image_file.read()
        
        plot_name = f"plot_{str(uuid.uuid4())}.png"
        plot_urls[plot_path] = await save_to_artifact_manager(plot_name, plot_content, artifact_manager)
        
    return plot_urls

async def get_data_files_dfs(data_file_names: List[str], artifact_manager: AriaArtifacts = None) -> List[pd.DataFrame]:
    if artifact_manager is None:
        return await asyncio.gather(*[read_df(file_path) for file_path in data_file_names])
    
    data_files = []
    for file_name in data_file_names:
        data_file = await artifact_manager.get_attachment(file_name)
        data_files.append((file_name, data_file.content))
        
    return await asyncio.gather(*[read_df(file_path, file_content) for (file_path, file_content) in data_files])

async def get_pai_agent(session_id: str, data_file_names: List[str], artifact_manager: AriaArtifacts = None) -> tuple[PaiAgent, Role]:
    data_files_dfs = await get_data_files_dfs(data_file_names, artifact_manager)
    project_folder = get_project_folder(session_id)
    pai_llm = PaiOpenAI()
    pai_agent_config = {
        'llm': pai_llm,
        'save_charts': True,
        'save_charts_path': project_folder,
        'max_retries': AGENT_MAX_RETRIES,
    }
    pai_agent = PaiAgent(data_files_dfs, config=pai_agent_config, memory_size=25)
    
    return pai_agent

def query_pai_agent(pai_agent: PaiAgent, query: str) -> str:
    request = f"""Analyze the data files and respond to the following request: ```{query}```
        
    Every time you save a plot, you MUST save it to a different filename. 
    If you make any plots at any point, you MUST include the file locations in your final explanation.
    When saving charts during CodeCleaning, you MUST save all the files to unique filenames.
    """
    response = pai_agent.chat(request)
    explanation = pai_agent.explain()
    logs = pai_agent.logs
    return response, explanation, logs

async def get_plot_paths(response: str, explanation: str, pai_logs: str, llm_model: str, event_bus: EventBus, constraints: str) -> PlotPaths:
    return await ask_agent(
        name="Analysis summarizer",
        instructions="You are a data science manager. You read the responses from a data science bot performing analysis and make sure it is suitable to pass on to the end-user as serializable output.",
        messages=[
            """Extract the paths to the plots or any .png files created by the data analysis bot.
                Get this information from the data analysis bot's final response, explanation, and logs.
                When creating your own explanations for the plots, refer to the input files used for the plots by their file names.
                If no plots were created, return an empty list. The bot's response and explanation is the following:""",
            f"Response: {response}\n\nExplanation: {explanation}",
            "The bot's logs are the following:",
            str(pai_logs),
        ],
        output_schema=PlotPaths,
        llm_model=llm_model,
        event_bus=event_bus,
        constraints=constraints,
    )

def create_explore_data(artifact_manager: AriaArtifacts = None, llm_model: str = "gpt2") -> Callable:
    @schema_tool
    async def explore_data(
        explore_request: str = Field(
            description="A request to explore the data files",
        ),
        data_files: List[str] = Field(
            description="List of file names or file paths of the files to analyze. Files must be in tabular (csv, tsv, excel, txt) format.",
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied to the data analysis",
        ),
    ) -> Dict[str, str]:
        """Analyzes or explores data files using a PandasAI data analysis agent. 
        Returns the agent's final response, explanation, logs, and plot urls. Make sure to look at the logs and plot 
        urls to get the full picture of the bot's work. If the bot created any plots, make sure to include the plot urls 
        and their meanings. Each function call creates at most one output plot, so if multiple plots are required the function must be once for each desired output plot"""

        session_id = get_session_id(current_session)
        pai_agent = await get_pai_agent(session_id, data_files, artifact_manager)
        response, explanation, pai_logs = query_pai_agent(pai_agent, explore_request)
        event_bus = artifact_manager.get_event_bus() if artifact_manager else None
        plot_paths = await get_plot_paths(response, explanation, pai_logs, llm_model, event_bus, constraints)
        plot_urls = await upload_plots(plot_paths, artifact_manager)

        return {
            "data_analysis_agent_final_response": str(response),
            "data_analysis_agent_final_explanation": explanation,
            "plot_urls": plot_urls,
        }
    return explore_data

async def main():
    parser = argparse.ArgumentParser(description="Analyze data files from a scientific experiment")
    parser.add_argument(
        "--user_request",
        type=str,
        help="The user request to create a study around",
        required=True,
    )
    parser.add_argument(
        "--constraints",
        type=str,
        help="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        default="",
    )
    args = parser.parse_args()
    artifact_manager = None
    config = load_config()
    llm_model = config["llm_model"]
    run_data_analyzer = create_explore_data(artifact_manager, llm_model)
    await run_data_analyzer(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)



    