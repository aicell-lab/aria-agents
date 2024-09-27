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
from schema_agents import schema_tool, Role
from pydantic import BaseModel, Field
import json
import os
import asyncio
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

# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "config.json")
with open(config_file, "r") as file:
    CONFIG = json.load(file)

def read_df(file_path : str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1]
    if ext == ".csv":
        return pd.read_csv(file_path)
    elif ext == ".tsv":
        return pd.read_csv(file_path, sep='\t')
    elif ext == ".xlsx":
        return pd.read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format ({ext}): {file_path}")
    
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

def get_pai_agent(data_files: List[str], save_charts_path: str) -> PaiAgent:
    dataframes = [read_df(file_path) for file_path in data_files]
    pai_llm = PaiOpenAI()
    pai_agent_config = {
        'llm' : pai_llm,
        'save_chargs' : True,
        'save_charts_path' : save_charts_path,
        'open_charts' : True,
        'max_retries' : 10 # default is 3
    }
    pai_agent = PaiAgent(dataframes, config = pai_agent_config, memory_size = 25)
    return pai_agent

def create_analyzer_function(data_store: HyphaDataStore = None) -> Callable:

    @schema_tool
    async def analyze_data_files(
        user_request : str = Field(
            description="A user request to analyze data files generated from a scientific experiment",
        ),
        project_name : str = Field(
            description="The name of the project, used to create a folder to store the output files",
        ),
        constraints : str = Field(
            "",
            description="Any constraints on the analysis",
        ),
    ) -> Dict[str, str]: 
        """Analyzes the data files generated from a scientific experiment using a recruited AI agent that has access to the files.
        Files must be in tabular (csv, tsv, excel) format. 
        Returns the response and explanation from the agent."""
        
        project_folder, data_folder, _ = get_analyzer_folders(project_name, "PROJECT_FOLDERS", "./projects")
        data_files = get_data_files(data_folder)
        pai_agent = get_pai_agent(data_files, project_folder)

        response = pai_agent.chat(user_request)
        explanation = pai_agent.explain()

        return {
            "response" : response,
            "explanation" : explanation
        }
    
    return analyze_data_files

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



        



# async def main():
#     data_store = HyphaDataStore()
#     data_analyst = create_analyzer_function(data_store=data_store)
#     result = await data_analyst()


# if __name__ == "__main__":
#     # asyncio.run(main())
#     # asyncio.run("0.0.0.0")
#     asyncio.run(main())