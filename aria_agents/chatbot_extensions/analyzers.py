import argparse
import os
import asyncio
import json
import uuid
from io import StringIO
from typing import List, Callable, Dict
import dotenv
from pydantic import BaseModel, Field
import pandas as pd
from pandas.errors import EmptyDataError
from pandasai.llm import OpenAI as PaiOpenAI
from pandasai import Agent as PaiAgent
from schema_agents import schema_tool, Role
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session
from schema_agents.utils.common import EventBus
from aria_agents.utils import get_project_folder
from aria_agents.artifact_manager import ArtifactManager
dotenv.load_dotenv()

AGENT_MAX_RETRIES = 5

# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "config.json")
with open(config_file, "r", encoding="utf-8") as file:
    CONFIG = json.load(file)

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

def get_session_id() -> str:
    pre_session = current_session.get()
    session_id = pre_session.id if pre_session else str(uuid.uuid4())
    return session_id

class PlotPaths(BaseModel):
    """A list of file paths to the plots (or any .png files) created by the data analysis bot"""
    plot_paths: List[str] = Field(description="A list of paths to the .png files created by the data analysis bot")
    plot_meanings: List[str] = Field(description="A list of meanings of the plots, why they were created and what they show")

async def get_plot_paths(response: str,
                        explanation: str,
                        pai_logs: List[Dict[str, str]],
                        summarizer_agent: Role,
                        session_id: str = None) -> PlotPaths:
    """Extracts the urls to the plots from the data analysis bot's response (if any were created by the bot) and includes an explanation for each plot"""
    response_with_explanation = f"Response: {response}\n\nExplanation: {explanation}"
    async with create_session_context(id=session_id, role_setting=summarizer_agent.role_setting):
        res = await summarizer_agent.aask(
            ["""Extract the paths to the plots or any .png files created by the data analysis bot.
             Get this information from the data analysis bot's final response, explanation, and logs.
             When creating your own explanations for the plots, refer to the input files used for the plots by their file names.
             If no plots were created, return an empty list. The bot's response and explanation is the following:""",
             response_with_explanation,
             "The bot's logs are the following:",
             str(pai_logs),
            ],
            output_schema=PlotPaths,
        )
    return res

async def upload_plots(plot_paths: PlotPaths, project_name: str, artifact_manager: ArtifactManager) -> Dict[str, str]:
    plot_urls = {}
    for plot_path in plot_paths.plot_paths:
        with open(plot_path, "rb") as image_file:
            plot_content = image_file.read()
    
        plot_name_base = f"plot_{str(uuid.uuid4())}"
        plot_id = await artifact_manager.put(
            value=plot_content,
            name=f"{project_name}:{plot_name_base}.png",
        )
        plot_urls[plot_path] = await artifact_manager.get_url(plot_id)
        
    return plot_urls

async def get_data_files_dfs(data_file_names: List[str], artifact_manager: ArtifactManager = None) -> List[pd.DataFrame]:
    if artifact_manager is None:
        return await asyncio.gather(*[read_df(file_path) for file_path in data_file_names])
    
    data_files = []
    for file_name in data_file_names:
        data_file = await artifact_manager.get_attachment(file_name)
        data_files.append((file_name, data_file.content))
        
    return await asyncio.gather(*[read_df(file_path, file_content) for (file_path, file_content) in data_files])

async def get_pai_agent(project_name: str, data_file_names: List[str], artifact_manager: ArtifactManager = None) -> tuple[PaiAgent, Role]:
    data_files_dfs = await get_data_files_dfs(data_file_names, artifact_manager)
    project_folder = get_project_folder(project_name)
    pai_llm = PaiOpenAI()
    pai_agent_config = {
        'llm': pai_llm,
        'save_charts': True,
        'save_charts_path': project_folder,
        'max_retries': AGENT_MAX_RETRIES,
    }
    pai_agent = PaiAgent(data_files_dfs, config=pai_agent_config, memory_size=25)
    
    return pai_agent

def get_summarizer_agent(constraints: str, llm_model: str, event_bus: EventBus = None) -> Role:
    return Role(
        name="Analysis summarizer",
        instructions="You are a data science manager. You read the responses from a data science bot performing analysis and make sure it is suitable to pass on to the end-user as serializable output.",
        icon="🤖",
        constraints=constraints,
        event_bus=event_bus,
        register_default_events=True,
        model=llm_model,
    )

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

async def get_or_create_agent(agent_dict, session_id, create_agent_func, *args):
    agent = agent_dict.get(session_id)
    if agent is None:
        agent = await create_agent_func(*args) if asyncio.iscoroutinefunction(create_agent_func) else create_agent_func(*args)
        agent_dict[session_id] = agent
    
    return agent

def create_explore_data(artifact_manager: ArtifactManager = None) -> Callable:
    summarizer_agents = {}
    pai_agents = {}

    @schema_tool
    async def explore_data(
        explore_request: str = Field(
            description="A request to explore the data files",
        ),
        data_files: List[str] = Field(
            description="List of file names or file paths of the files to analyze. Files must be in tabular (csv, tsv, excel, txt) format.",
        ),
        project_name: str = Field(
            description="The name of the project, used to create a folder to store the output files",
        ),
        constraints: str = Field(
            "",
            description="Specify any constraints that should be applied to the data analysis",
        ),
    ) -> Dict[str, str]:
        """Analyzes or explores data files using a PandasAI data analysis agent, initializing it if necessary. 
        Returns the agent's final response, explanation, logs, and plot urls. Make sure to look at the logs and plot 
        urls to get the full picture of the bot's work. If the bot created any plots, make sure to include the plot urls 
        and their meanings. Each function call creates at most one output plot, so if multiple plots are required the function must be once for each desired output plot"""

        event_bus = artifact_manager.get_event_bus() if artifact_manager else None
        session_id = get_session_id()
        pai_agent = await get_or_create_agent(pai_agents, session_id, get_pai_agent, project_name, data_files, artifact_manager)
        summarizer_agent = await get_or_create_agent(summarizer_agents, session_id, get_summarizer_agent, constraints, CONFIG["llm_model"], event_bus)
        
        response, explanation, pai_logs = query_pai_agent(pai_agent, explore_request)
        plot_paths = await get_plot_paths(response=response,
                                        explanation=explanation,
                                        pai_logs=pai_logs,
                                        summarizer_agent=summarizer_agent,
                                        session_id=session_id)
        
        plot_urls = plot_paths.plot_paths if artifact_manager is None else await upload_plots(plot_paths, project_name, artifact_manager)

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
        "--project_name",
        type=str,
        help="The name of the project, used to create a folder to store the output files",
        default="test",
    )
    parser.add_argument(
        "--constraints",
        type=str,
        help="Specify any constraints that should be applied for compiling the experiments, for example, instruments, resources and pre-existing protocols, knowledge etc.",
        default="",
    )
    args = parser.parse_args()
    artifact_manager = None
    run_data_analyzer = create_explore_data(artifact_manager)
    await run_data_analyzer(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)



    