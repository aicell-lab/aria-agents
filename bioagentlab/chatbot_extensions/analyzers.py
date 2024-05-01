import dotenv
dotenv.load_dotenv()
import argparse
import os
import pandas as pd
from contextlib import redirect_stdout
from io import StringIO
import asyncio
from typing import List
import asyncio
import shutil
import dotenv
from schema_agents import schema_tool, Role
from pydantic import BaseModel, Field
from langchain_experimental.tools.python.tool import PythonAstREPLTool
from contextlib import redirect_stdout
from io import StringIO


def flatten_model_description(json_data):
    flattened = {}

    def flatten_section(section, prefix=''):
        for key, value in section.items():
            if isinstance(value, dict):
                if 'description' in value:
                    # Adding the description of the current section/item to the flat dictionary
                    flattened[f'{prefix}{key}'] = value['description']
                    # print(key, value['description'])
                if 'properties' in value or '$defs' in value or 'items' in value:
                    # Recursively flatten nested sections
                    # new_prefix = f'{prefix}{key}.' if prefix else f'{key}.'
                    new_prefix = ""
                    flatten_section(value.get('properties', {}), new_prefix)
                    flatten_section(value.get('$defs', {}), new_prefix)
                    if 'items' in value and isinstance(value['items'], dict):
                        flatten_section(value['items'], new_prefix)
                if len(value.keys()) == 1 and '$ref' in value:
                    flattened[f'{key}'] = flattened[value['$ref'].split('/')[-1]] # gkreder
                else:
                    flatten_section(value)
            elif isinstance(value, list):
                # For items that are lists, we assume they might contain references or nested objects
                for item in value:
                    if isinstance(item, dict):
                        flatten_section(item, prefix)
    # Start the flattening process with the top-level items
    flatten_section(json_data)
    return flattened

def flatten_dict(d, num_hashes, flattened_schema, ignore_keys=[]):
    """Flatten a nested dictionary into a string with indentation."""
    flat_str = ""
    for key, value in d.items():
        if key in ignore_keys:
            continue
        flat_str += "#" * num_hashes + f" {str(key)} ({flattened_schema[key]})"
        if isinstance(value, dict):
            flat_str += "\n" + flatten_dict(value, num_hashes+1, flattened_schema, ignore_keys = ignore_keys)
        else:
            flat_str += '\n' + str(value) + "\n\n"
    return flat_str

async def main():
    parser = argparse.ArgumentParser(description='Run hypothesis testing on experimental data')
    parser.add_argument('--investigation_file', type=str, help='The path to the ISA investigation file')
    parser.add_argument('--study_file', type=str, help='The path to the ISA study file')
    parser.add_argument('--metabolite_file', type=str, help='The path to the metabolite intensity file')
    parser.add_argument('--output_dir', type=str, help='The directory to save the output files', default = 'analysis')
    parser.add_argument('--hypothesis', type=str, help='The hypothesis to test')
    args = parser.parse_args()

    
    os.makedirs(args.output_dir, exist_ok=True)

    try:
        for fname in [args.investigation_file, args.study_file, args.metabolite_file]:
            shutil.copy(fname, args.output_dir)

        i_text = open(args.investigation_file).read()

        df_s = pd.read_csv(args.study_file, sep = '\t')
        df_s_slim = df_s[[x for x in df_s.columns if not x.lower().startswith("term")]]
        s_temp_file = os.path.join(args.output_dir, "s_temp.tsv")
        df_s_slim.to_csv(s_temp_file, sep = '\t', index = False)
        s_text = open(s_temp_file).read()
        df = pd.read_csv(args.metabolite_file, sep = '\t')

        investigation_scraper = Role(name = "investigation_scraper",
                            instructions = "Reads ISA-Tab investigation file content and summarizes the relevant details about what experiments were performed and how. This includes samples, experimental conditions, preparation, etc. Do NOT include anything about the paper's findings or results, only its setup, samples, experiments, etc.",
                            constraints=None,
                            register_default_events=True,
                            model="gpt-4-turbo-preview"
                        )

        class InvestigationSummary(BaseModel):
            """A summary of the investigation file containing all information needed to use these samples in an analysis pipeline."""
            i_file_summary : str = Field(..., description="The summary of the investigation file containing all information needed to use these samples in an analysis pipeline.")

        investigation_summary = await investigation_scraper.aask(i_text, InvestigationSummary)


        class HypothesisWithInvestigation(BaseModel):
            """A hypothesis to test on data from experiments along with the description of the experiments"""
            hypothesis: str = Field(..., description="The hypothesis to test")
            investigation_summary: InvestigationSummary = Field(..., description="The summary of the investigation file containing all information needed to use these samples in an analysis pipeline.")
            s_text : str = Field(..., description = "The content of the sample file containing all the sample names and metadata")

        class SampleSummary(BaseModel):
            """A condensed summary of which samples are relevant to test the hypothesis and how they are relevant"""
            relevant_samples : List[str] = Field(..., description="A list of the relevant samples to test the hypothesis")
            sample_mapping : str = Field(..., description="A summary of which samples correspond to which conditions")
            condition_mapping : str = Field(..., description = "How the conditions are relevant to the hypothesis")

        sample_summarizer = Role(name = "sample_summarizer",
                            instructions = "Read the investigation summary and hypothesis. Then look at the contents of the sample file and identify exactly with samples are relevant to testing the hypothesis.",
                            constraints=None,
                            register_default_events=True,
                            model="gpt-4-turbo-preview"
                        )

        hypothesis_with_investigation = HypothesisWithInvestigation(hypothesis=args.hypothesis, investigation_summary=investigation_summary, s_text=s_text)
        sample_summary = await sample_summarizer.aask(hypothesis_with_investigation, SampleSummary)

        class TestPackage(BaseModel):
            """A package containing all the information needed to test a hypothesis"""
            hypothesis_with_investigation : HypothesisWithInvestigation = Field(..., description="The hypothesis to test along with the description of the experiments")
            sample_summary : SampleSummary = Field(..., description="A condensed summary of which samples are relevant to test the hypothesis and how they are relevant")
            metabolite_ids : List[str] = Field(..., description="The list of metabolite identifiers in the metabolite intensity DataFrame")
            metabolite_names : List[str] = Field(..., description="The list of human-interpretable metabolite names in the metabolite intensity DataFrame (each entry corresponds to the same entry in the `metabolite_ids` list)")
            df_head : str = Field(..., description = "The first few rows of the metabolite intensity DataFrame (the header row and the first two rows of data)")

        metabolite_names = list(df['metabolite_identification'].values)
        metabolite_ids = list(df['database_identifier'].values)

        test_package = TestPackage(hypothesis_with_investigation=HypothesisWithInvestigation(hypothesis=args.hypothesis, investigation_summary=investigation_summary, s_text="Full s_text not included here, refer to sample summaries"),
                                sample_summary=sample_summary,
                                metabolite_ids=metabolite_ids,
                                metabolite_names=metabolite_names,
                                df_head=df.head(2).to_string())
        
        flattened_schema = flatten_model_description(test_package.model_json_schema())
        flattened_test_package = flatten_dict(test_package.model_dump(), 1, flattened_schema, ignore_keys=["s_text", "df_head"])
        os.makedirs(args.output_dir, exist_ok=True)
        with open(os.path.join(args.output_dir, f"test_package_description.md"), "w") as f:
            f.write(flattened_test_package)

        df_locals = {}
        df_locals['df'] = df.copy()
        tool = PythonAstREPLTool(globals = df_locals)
        io_buffer = StringIO()

        @schema_tool
        async def dataframe_analysis(python_cmd : str = Field(..., description = "The Python command to execute in a live REPL")):
            """Run a Python command for the overall purpose of analyzing the Pandas dataframe. Your commands can refer to `df` which is already loaded in the environment as a pandas dataframe.
            Other than that you must import any necessary libraries in the sequence of commands. Beyond that, libraries such as pandas, scipy, numpy, sklearn, etc can all be used after being imported. What you will receive in return is the standard output of your command.
            You imports and variables DO persist across commands. So you can define a variable in one command and use it in the next. Do NOT modify `df` since it is a persistent variable. Copy it to another variable and modify those accordingly.
            Note that if you run some commands and receive an empty string as response, it means the code executed without any errors and you can keep going."""    
            with redirect_stdout(io_buffer):
                res = tool.invoke(python_cmd)
                return res
            
        analyzer = Role(name = "analyzer",
                        instructions = "You are an expert statistician and scientist. Your job is to take the data from an experiment together with a hypothesis and test the hypothesis in its entirety via `dataframe_analysis`. `df` is a pandas dataframe containing the experimental data. Descriptions of the experiment and samples will be provided to you. The commands can refer to `df` which is already loaded in your environment as a pandas dataframe. Other than that you must import any necessary libraries in the sequence of commands.",
                        constraints=None,
                        register_default_events=True,
                        model="gpt-4-turbo-preview")

        class AnalysisResults(BaseModel):
            """The COMPLETE results of the analysis of the hypothesis on the data"""
            analysis_results : str = Field(..., description="The results of the analysis of the hypothesis on the data")
            steps_taken : str = Field(..., description="A summary of the steps taken to analyze the hypothesis on the data")
            python_commands : List[str] = Field(..., description="ALL the Python commands that were executed to analyze the hypothesis on the data (include all the commands that worked, don't include any you had to fix. And include comments as well)")

        analysis, analysis_metadata = await analyzer.acall(test_package, tools = [dataframe_analysis], return_metadata = True, output_schema = AnalysisResults)


        with open(os.path.join(args.output_dir, f"analysis_results.txt"), "w") as f:
            f.write(f"# Hypothesis\n{args.hypothesis}\n\n# Conclusion\n{analysis.analysis_results}\n\n# Steps Taken\n{analysis.steps_taken}\n\n")
        with open(os.path.join(args.output_dir, f"python_script.py"), "w") as f:
            f.write("\n".join(analysis.python_commands))
        with open(os.path.join(args.output_dir, f"acall_steps.txt"), "w") as f:
            print(analysis_metadata, file=f)
    
    except Exception as e:
        print(f"Failed to analyze hypothesis: {e}")

if __name__ == "__main__":
    asyncio.run(main())



