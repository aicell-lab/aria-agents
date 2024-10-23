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

def create_explore_data(data_store: HyphaDataStore = None) -> Callable:
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
    ) -> Dict[str, str]:
        """Analyzes or explores data files using a PandasAI agent, initializing it if necessary."""
        session_id = get_session_id()
        pai_agent = pai_agents.get(session_id)
        
        if pai_agent is None:
            # Initialize the PandasAI agent
            data_files_dfs = await asyncio.gather(*[read_df(file_path) for file_path in data_files])
            project_folder, _, _ = get_analyzer_folders(project_name, "PROJECT_FOLDERS", "./projects")
            pai_llm = PaiOpenAI()
            pai_agent_config = {
                'llm': pai_llm,
                'save_charts': True,
                'save_charts_path': project_folder,
                'open_charts': True,
            }
            pai_agent = PaiAgent(data_files_dfs, config=pai_agent_config, memory_size=25)
            pai_agents[session_id] = pai_agent
        
        response = pai_agent.chat(explore_request)
        explanation = pai_agent.explain()
        plot_url = None
        plot_content_base64 = None

        if type(response) == str and os.path.isfile(response) and response.lower().endswith(".png"):
            with open(response, "rb") as image_file:
                plot_content = image_file.read()
                plot_content_base64 = base64.b64encode(plot_content).decode('utf-8')

            if data_store is not None:
                plot_name_base = f"plot_{str(uuid.uuid4())}"
                plot_id = data_store.put(
                    obj_type="file",
                    # value=response,
                    value=plot_content,
                    name=f"{project_name}:{plot_name_base}.png",
                )
                plot_url = data_store.get_url(plot_id)
            else:
                plot_url = response

        return {
            "response": response,
            "explanation": explanation,
            "plot_url": plot_url,
            "plot_content_base64": plot_content_base64
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



        



# async def main():
#     data_store = HyphaDataStore()
#     data_analyst = create_analyzer_function(data_store=data_store)
#     result = await data_analyst()


# if __name__ == "__main__":
#     # asyncio.run(main())
#     # asyncio.run("0.0.0.0")
#     asyncio.run(main())
