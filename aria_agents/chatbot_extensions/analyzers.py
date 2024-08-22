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
from aria_agents.chatbot_extensions.code_execution import execute_code
from schema_agents import Role, schema_tool
from imjoy_rpc.hypha import connect_to_server, login
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
    ext = os.path.splitext(file_path)[1]
    return ext in [".csv", ".tsv", ".xlsx"]


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
        pre_session = current_session.get()
        session_id = pre_session.id if pre_session else str(uuid.uuid4())

        project_folders = os.environ.get("PROJECT_FOLDERS", "./projects")
        project_folder = os.path.abspath(os.path.join(project_folders, project_name))
        data_folder = os.path.join(project_folder, "data")
        analysis_folder = os.path.join(project_folder, "analysis")
        for d in [project_folder, data_folder, analysis_folder]:
            os.makedirs(d, exist_ok=True)
        data_files = [os.path.join(data_folder, x) for x in os.listdir(data_folder) if os.path.isfile(os.path.join(data_folder, x)) and is_data_file(os.path.join(data_folder, x))]


        if data_store is None:
            event_bus = None
        else:
            event_bus = data_store.get_event_bus()

        dataframes = [read_df(file_path) for file_path in data_files]

        pai_llm = PaiOpenAI()
        pai_agent_config = {
            'llm' : pai_llm,
            'save_chargs' : True,
            'save_charts_path' : project_folder,
            'open_charts' : True,
            'max_retries' : 10 # default is 3
        }
        pai_agent = PaiAgent(dataframes, config = pai_agent_config, memory_size = 25)

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