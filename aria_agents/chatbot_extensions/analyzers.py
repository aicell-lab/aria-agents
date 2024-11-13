import argparse
import dotenv
dotenv.load_dotenv()
import os
import pandas as pd
import asyncio
from typing import List, Dict 
import asyncio
import shutil
import dotenv
from pandas.errors import EmptyDataError
from schema_agents import schema_tool, Role
from pydantic import BaseModel, Field
import json
import os
import asyncio
import base64
import json
# from hypha_store import HyphaDataStore
from aria_agents.hypha_store import HyphaDataStore
# from aria_agents.chatbot_extensions.code_execution import execute_code
from schema_agents import Role, schema_tool
from hypha_rpc import connect_to_server, login
from typing import List, Callable
from pydantic import BaseModel, Field
from langchain_experimental.tools.python.tool import PythonAstREPLTool
from schema_agents.role import create_session_context
from schema_agents.utils.common import current_session
import uuid
from pandasai.llm import OpenAI as PaiOpenAI
from pandasai import Agent as PaiAgent

AGENT_MAX_RETRIES = 5

# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "config.json")
with open(config_file, "r") as file:
    CONFIG = json.load(file)

async def read_df(file_path: str) -> pd.DataFrame:
    def _read_file(path):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".csv":
                return pd.read_csv(path)
            elif ext == ".tsv":
                return pd.read_csv(path, sep='\t')
            elif ext == ".xlsx":
                return pd.read_excel(path, engine='openpyxl')
            else:
                return pd.read_csv(path, sep=None, engine='python')
        except EmptyDataError:
            print(f"Warning: The file {path} is empty or contains no data.")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error reading file {path}: {str(e)}")
            raise ValueError(f"Unable to open file {path} as tabular file: {str(e)}")

    return await asyncio.get_event_loop().run_in_executor(None, _read_file, file_path)

def is_data_file(file_path : str) -> bool:
    if not os.path.isfile(file_path):
        return False
    
    ext = os.path.splitext(file_path)[1]
    return ext in [".csv", ".tsv", ".xlsx"]

def get_analyzer_folders(project_name: str, env_var: str, default_val: str) -> tuple[str]:
    project_folders = os.environ.get(env_var, default_val)
    project_folder = os.path.abspath(os.path.join(project_folders, project_name))
    data_folder = os.path.join(project_folder, "data")
    analysis_folder = os.path.join(project_folder, "analysis")
    
    for this_folder in [project_folder, data_folder, analysis_folder]:
            os.makedirs(this_folder, exist_ok=True)
    
    return project_folder, data_folder, analysis_folder

def get_session_id() -> str:
    pre_session = current_session.get()
    session_id = pre_session.id if pre_session else str(uuid.uuid4())
    return session_id

def get_data_files(data_folder: str) -> List[str]:
    data_listdir = os.listdir(data_folder)
    all_data_paths = [os.path.join(data_folder, data_item) for data_item in data_listdir]    
    data_files = filter(is_data_file, all_data_paths)
    return data_files

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
    async with create_session_context(id=session_id, role_setting=summarizer_agent._setting):
        res = await summarizer_agent.aask(
            ["""Extract the urls to the plots or any .png files created by the data analysis bot. 
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

def create_explore_data(data_store: HyphaDataStore = None) -> Callable:
    summarizer_agents = {}
    pai_agents = {}

    @schema_tool
    async def explore_data(
        explore_request: str = Field(
            description="A request to explore the data files",
        ),
        data_files: List[str] = Field(
            description="List of filepaths/urls of the files to analyze. Files must be in tabular (csv, tsv, excel, txt) format.",
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
        session_id = get_session_id()
        pai_agent = pai_agents.get(session_id)
        summarizer_agent = summarizer_agents.get(session_id)

        if data_store is None:
            event_bus = None
        else:
            event_bus = data_store.get_event_bus()
        
        if pai_agent is None:
            # Initialize the PandasAI agent
            data_files_dfs = await asyncio.gather(*[read_df(file_path) for file_path in data_files])
            project_folder, _, _ = get_analyzer_folders(project_name, "PROJECT_FOLDERS", "./projects")
            pai_llm = PaiOpenAI()
            pai_agent_config = {
                'llm': pai_llm,
                'save_charts': True,
                'save_charts_path': project_folder,
                # 'open_charts': True,
                'max_retries': AGENT_MAX_RETRIES,
            }
            pai_agent = PaiAgent(data_files_dfs, config=pai_agent_config, memory_size=25)
            pai_agents[session_id] = pai_agent
        
        if summarizer_agent is None:
            summarizer_agent = Role(
            name="Analysis summarizer",
            instructions="You are an data science manager. You read the responses from a data science bot performing analysis and make sure it is suitable to pass on to the end-user as serializable output.",
            icon="🤖",
            constraints=constraints,
            event_bus=event_bus,
            register_default_events=True,
            model=CONFIG["llm_model"],
        )
            summarizer_agents[session_id] = summarizer_agent
        
        pai_agent_request = f"""Analyze the data files and respond to the following request: ```{explore_request}```
        
        Every time you save a plot, you MUST save it to a different filename. 
        If you make any plots at any point, you MUST include the file locations in your final explanation.
        When saving charts during CodeCleaning, you MUST save all the files to unique filenames.
        """
        response = pai_agent.chat(pai_agent_request)
        explanation = pai_agent.explain()
        pai_logs = pai_agent.logs
        plot_paths = await get_plot_paths(response=response,
                                        explanation=explanation,
                                        pai_logs=pai_logs,
                                        summarizer_agent=summarizer_agent,
                                        session_id=session_id)
        
        plot_urls = {}
        for plot_path in plot_paths.plot_paths:
            with open(plot_path, "rb") as image_file:
                plot_content = image_file.read()
                plot_content_base64 = base64.b64encode(plot_content).decode('utf-8')
            if data_store is not None:
                plot_name_base = f"plot_{str(uuid.uuid4())}"
                plot_id = data_store.put(
                    obj_type="file",
                    value=plot_content,
                    name=f"{project_name}:{plot_name_base}.png",
                )
                plot_url = data_store.get_url(plot_id)
            else:
                plot_url = plot_path
            plot_urls[plot_path] = plot_url


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
    data_store = None
    run_data_analyzer = create_analyzer_function(data_store=data_store)
    await run_data_analyzer(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)



    