import argparse
import asyncio
import os
import base64
import tempfile
from io import StringIO
from typing import List, Callable, Optional
from pydantic import BaseModel, Field
import pandas as pd
from pandas.errors import EmptyDataError
from pandasai.llm import OpenAI as PaiOpenAI
from pandasai import Agent as PaiAgent
from schema_agents import schema_tool
from schema_agents.utils.common import current_session, EventBus
from aria_agents.utils import get_session_id, ask_agent, SchemaToolReturn, ArtifactFile, load_config, StatusCode

AGENT_MAX_RETRIES = 5

class DataAnalysisResult(BaseModel):
    """Results from data analysis"""
    analysis: str = Field(description="Main analysis results")
    explanation: str = Field(description="Detailed explanation of the analysis")
    plots: List[str] = Field(default=[], description="List of generated plot names")
    plot_explanations: List[str] = Field(default=[], description="Explanations for each generated plot")

class PlotInfo(BaseModel):
    """Information about generated plots"""
    plot_paths: List[str] = Field(description="Paths to the generated plots")
    plot_meanings: List[str] = Field(description="Explanations for each plot")

async def read_df(file_path: str, content: Optional[str] = None) -> pd.DataFrame:
    """Read a dataframe from a file path or content string"""
    def _read_file(path: str, content: Optional[str] = None) -> pd.DataFrame:
        ext = path.lower().split('.')[-1]
        file_obj = StringIO(content) if content else path
        
        try:
            if ext == 'csv':
                return pd.read_csv(file_obj)
            elif ext == 'tsv':
                return pd.read_csv(file_obj, sep='\t')
            elif ext == 'xlsx':
                return pd.read_excel(file_obj)
            else:
                return pd.read_csv(file_obj, sep=None, engine='python')
        except EmptyDataError:
            print(f"Warning: The file {path} is empty")
            return pd.DataFrame()
        except Exception as e:
            raise ValueError(f"Unable to read {path} as tabular data: {str(e)}") from e

    return await current_session.get().loop.run_in_executor(None, _read_file, file_path, content)

async def get_data_files_dfs(data_file_names: List[str], contents: Optional[List[str]] = None) -> List[pd.DataFrame]:
    """Load multiple dataframes from files or content strings"""
    if contents:
        return await asyncio.gather(*[read_df(name, content) for name, content in zip(data_file_names, contents)])
    return await asyncio.gather(*[read_df(name) for name in data_file_names])

def query_pai_agent(pai_agent: PaiAgent, query: str) -> tuple[str, str, str]:
    """Run a query through the PandasAI agent"""
    request = f"""Analyze the data files and respond to the following request: ```{query}```
        
    Every time you save a plot, you MUST save it to a different filename.
    When making plots, make sure they are clear and well-labeled.
    If you make any plots, you MUST explain what each one shows.
    """
    response = pai_agent.chat(request)
    explanation = pai_agent.explain()
    logs = pai_agent.logs
    return response, explanation, logs

async def get_plot_info(
    response: str,
    explanation: str,
    pai_logs: str,
    llm_model: str,
    event_bus: Optional[EventBus] = None,
    constraints: Optional[str] = None
) -> PlotInfo:
    """Extract plot information from the agent's response"""
    return await ask_agent(
        name="Analysis summarizer",
        instructions="You are a data science manager. You read the responses from a data science bot performing analysis and extract information about any plots created.",
        messages=[
            """Extract the paths to any plots created by the data analysis bot and explain what each one shows.
            Get this information from the bot's response, explanation, and logs.
            When creating plot explanations, refer to the input files used by their names.
            If no plots were created, return empty lists. Here is the bot's output:""",
            f"Response: {response}\n\nExplanation: {explanation}",
            "The bot's logs are:",
            str(pai_logs),
        ],
        output_schema=PlotInfo,
        llm_model=llm_model,
        event_bus=event_bus,
        constraints=constraints,
    )

def create_explore_data(llm_model: str = "gpt2", event_bus: Optional[EventBus] = None) -> Callable:
    @schema_tool
    async def explore_data(
        explore_request: str = Field(
            description="A request to explore the data files"
        ),
        data_files: List[str] = Field(
            description="List of file paths to analyze. Files must be tabular (csv, tsv, excel, txt)"
        ),
        data_contents: Optional[List[str]] = Field(
            None,
            description="Optional list of file contents if files should not be read from disk"
        ),
        constraints: str = Field(
            "",
            description="Optional constraints for the analysis"
        ),
    ) -> SchemaToolReturn:
        """Analyzes data files using PandasAI. Can work with local files or provided file contents."""
        
        # Set up temporary directory for plots
        temp_dir = tempfile.mkdtemp()
        try:
            # Initialize PandasAI
            try:
                data_files_dfs = await get_data_files_dfs(data_files, data_contents)
            except Exception as e:
                return SchemaToolReturn.error(f"Failed to read data files: {str(e)}", 400)
            pai_agent = PaiAgent(
                data_files_dfs,
                config={
                    'llm': PaiOpenAI(),
                    'save_charts': True,
                    'save_charts_path': temp_dir,
                    'max_retries': AGENT_MAX_RETRIES
                },
                memory_size=25
            )
            
            # Run analysis
            try:
                response, explanation, pai_logs = query_pai_agent(pai_agent, explore_request)
                plot_info = await get_plot_info(response, explanation, pai_logs, llm_model, event_bus, constraints)
            except Exception as e:
                return SchemaToolReturn.error(f"Analysis failed: {str(e)}", 500)
            
            # Convert plots to base64 and prepare artifacts
            to_save = []
            failed_plots = []
            for i, (plot_path, meaning) in enumerate(zip(plot_info.plot_paths, plot_info.plot_meanings)):
                try:
                    with open(plot_path, 'rb') as f:
                        plot_content = f.read()
                        base64_content = base64.b64encode(plot_content).decode('utf-8')
                    plot_name = f"plot_{i}.png"
                    to_save.append(ArtifactFile(
                        name=plot_name,
                        content=base64_content
                    ))
                except Exception as e:
                    failed_plots.append(f"{plot_path}: {str(e)}")
            
            # Create analysis result
            result = DataAnalysisResult(
                analysis=response,
                explanation=explanation,
                plots=[f.name for f in to_save],
                plot_explanations=plot_info.plot_meanings
            )

            # Determine status based on plot generation success
            if failed_plots:
                status = StatusCode(
                    code=206,  # Partial content
                    message=f"Analysis completed with {len(failed_plots)} failed plots",
                    type="success"
                )
            else:
                num_plots = len(to_save)
                status = StatusCode.ok(
                    f"Analysis completed successfully with {num_plots} plot{'s' if num_plots != 1 else ''}"
                )
            
            return SchemaToolReturn(
                to_save=to_save,
                response=result,
                status=status
            )
            
        except Exception as e:
            return SchemaToolReturn.error(f"Unexpected error during analysis: {str(e)}", 500)
            
        finally:
            # Clean up temporary files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

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
    config = load_config()
    llm_model = config["llm_model"]
    run_data_analyzer = create_explore_data(llm_model)
    await run_data_analyzer(**vars(args))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(e)
