
import os
import sys
import io
import contextlib
import ast
import traceback
import array
import wave
import asyncio
import json
import ipdb


import base64
from functools import partial
# from hypha_store import HyphaDataStore
from aria_agents.hypha_store import HyphaDataStore
from schema_agents import Role, schema_tool
from imjoy_rpc.hypha import connect_to_server, login
from typing import List, Callable
from pydantic import BaseModel, Field
from langchain_experimental.tools.python.tool import PythonAstREPLTool

# code execution from Wanlu code
class OutputRecorder:
    def __init__(self):
        self.outputs = []

    def write(self, type, content):
        self.outputs.append({"type": type, "content": content})
    
    def show(self, type, content, attrs={}):
        self.outputs.append({"type": type, "content": content, "attrs": attrs})


# For redirecting stdout and stderr later.
class JSOutWriter(io.TextIOBase):
    def __init__(self, recorder):
        self._recorder = recorder

    def write(self, s):
        return self._recorder.write("stdout", s)

class JSErrWriter(io.TextIOBase):
    def __init__(self, recorder):
        self._recorder = recorder

    def write(self, s):
        return self._recorder.write("stderr", s)

def setup_matplotlib(output_recorder, store):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    def show():
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        # img = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
        # output_recorder.show("img", img)
        file_id = store.put('file', buf.getvalue(), 'plot.png')
        output_recorder.show("img", store.get_url(file_id))
        plt.clf()

    plt.show = show

def show_image(output_recorder, store, image, **attrs):
    from PIL import Image
    if not isinstance(image, Image.Image):
        image = Image.fromarray(image)
    buf = io.BytesIO()
    image.save(buf, format='png')
    # data = 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
    file_id = store.put('file', buf.getvalue(), 'plot.png')
    output_recorder.show("img", store.get_url(file_id))

def show_animation(output_recorder, store, frames, duration=100, format="apng", loop=0, **attrs):
    from PIL import Image
    buf = io.BytesIO()
    img, *imgs = [frame if isinstance(frame, Image.Image) else Image.fromarray(frame) for frame in frames]
    img.save(buf, format='png' if format == "apng" else format, save_all=True, append_images=imgs, duration=duration, loop=0)
    # img = f'data:image/{format};base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
    # output_recorder.show("img", img, attrs)
    file_id = store.put('file', buf.getvalue(), 'plot.png')
    output_recorder.show("img", store.get_url(file_id))

def convert_audio(data):
    try:
        import numpy as np
        is_numpy = isinstance(data, np.ndarray)
    except ImportError:
        is_numpy = False
    if is_numpy:
        if len(data.shape) == 1:
            channels = 1
        if len(data.shape) == 2:
            channels = data.shape[0]
            data = data.T.ravel()
        else:
            raise ValueError("Too many dimensions (expected 1 or 2).")
        return ((data * (2**15 - 1)).astype("<h").tobytes(), channels)
    else:
        data = array.array('h', (int(x * (2**15 - 1)) for x in data))
        if sys.byteorder == 'big':
            data.byteswap()
        return (data.tobytes(), 1)

def show_audio(output_recorder, store, samples, rate):
    bytes, channels = convert_audio(samples)
    buf = io.BytesIO()
    with wave.open(buf, mode='wb') as w:
        w.setnchannels(channels)
        w.setframerate(rate)
        w.setsampwidth(2)
        w.setcomptype('NONE', 'NONE')
        w.writeframes(bytes)
    # audio = 'data:audio/wav;base64,' + base64.b64encode(buf.getvalue()).decode('utf-8')
    # output_recorder.show("audio", audio)
    file_id = store.put('file', buf.getvalue(), 'audio.wav')
    output_recorder.show("audio", store.get_url(file_id))



def preprocess_code(source):
    """Parse the source code and separate it into main code and last expression."""
    parsed_ast = ast.parse(source)
    
    last_node = parsed_ast.body[-1] if parsed_ast.body else None
    
    if isinstance(last_node, ast.Expr):
        # Separate the AST into main body and last expression
        main_body_ast = ast.Module(body=parsed_ast.body[:-1], type_ignores=parsed_ast.type_ignores)
        last_expr_ast = last_node
        
        # Convert main body AST back to source code for exec
        main_body_code = ast.unparse(main_body_ast)
        
        return main_body_code, last_expr_ast
    else:
        # If the last node is not an expression, treat the entire code as the main body
        return source, None
    

async def execute_code(store, source, context):
    # HACK: Prevent 'wave' import from failing because audioop is not included with pyodide.
    import types
    embed = types.ModuleType('embed')
    sys.modules['embed'] = embed
    output_recorder = OutputRecorder()

    embed.image = partial(show_image, output_recorder, store)
    embed.animation = partial(show_animation, output_recorder, store)
    embed.audio = partial(show_audio, output_recorder, store)

    out = JSOutWriter(output_recorder)
    err = JSErrWriter(output_recorder)
   
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            setup_matplotlib(output_recorder, store)
            source, last_expression = preprocess_code(source)
            code = compile(source, "<string>", "exec", ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)

            result = eval(code, context)
            if result is not None:
                result = await result
            if last_expression:
                if isinstance(last_expression.value, ast.Await):
                    # If last expression is an await, compile and execute it as async
                    last_expr_code = compile(ast.Expression(last_expression.value), "<string>", "eval", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
                    result = await eval(last_expr_code, context)
                else:
                    # If last expression is not an await, compile and evaluate it normally
                    last_expr_code = compile(ast.Expression(last_expression.value), "<string>", "eval")
                    result = eval(last_expr_code, context)
                if result is not None:
                    print(result)
            return output_recorder.outputs
        except:
            traceback.print_exc()
            raise

class FileDescriptions(BaseModel):
    """A detailed overview of files generated from a scientific study produced from exploring the files"""
    file_list : List[str] = Field(..., description="List of files explored")
    file_formats : List[str] = Field(..., description="The format (file extension) for each file")
    file_format_notes : List[str] = Field(..., description="Detailed notes on the format of each file - for example, .txt files may be tab-delimited or have some structure not captured by the file extension. If there is tabular data, describe the contents of the columns.")
    file_contents : List[str] = Field(..., description="Detailed description of the contents of each file")
    study_description : str = Field(..., description="A best-guess detailed description of the scientific study that produced these files based on the file contents. This should include the type of study, hypotheses tested, organisms used, equipment used, procedures followed, and any other relevant information.")

class DataHypothesis(BaseModel):
    """A hypothesis that can be tested about the data generated from a scientific study"""
    hypothesis : str = Field(..., description="The hypothesis to test on the data generated from a scientific study")
    justification : str = Field(..., description="Justification for the hypothesis based on the file contents and study description")
    procedure : str = Field(..., description="A detailed procedure to test the hypothesis using Python on the data generated from a scientific study")
    visualization : str = Field(..., description="A plan for how to visualize the results of the hypothesis test")

class DataHypotheses(BaseModel):
    """A list of hypotheses that can be tested about the data generated from a scientific study"""
    hypotheses : List[DataHypothesis] = Field(..., description="A list of hypotheses to test on the data generated from a scientific study")

class HypothesisCode(BaseModel):
    """Code to test a hypothesis on the data generated from a scientific study"""
    code : str = Field(..., description="Python code to test a hypothesis on the data generated from a scientific study. The result of the code should be a visualization of the results of the hypothesis test in a shown matplotlib plot. In addition to the visualization, the plot should include a text box with the hypothesis, procedure, and results summary of the hypothesis test.")

class HypothesisCodes(BaseModel):
    """Code to test a list of hypotheses on the data generated from a scientific study"""
    codes : List[HypothesisCode] = Field(..., description="A list of Python code snippets to test hypotheses on the data generated from a scientific study. The result of each code snippet should be a visualization of the results of the hypothesis test in a shown matplotlib plot. In addition to the visualization, the plot should include a text box with the hypothesis, procedure, and results summary of the hypothesis test.")



# Load the configuration file
this_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(this_dir, "config.json")
with open(config_file, "r") as file:
    CONFIG = json.load(file)


def create_analyzer_function(data_store: HyphaDataStore = None) -> Callable:
    @schema_tool
    async def run_code(code : str = Field(..., description="Python code to execute")):
        """Given Python code, executes the code and returns the output"""
        result = await execute_code(data_store, code, {})
        return {
            "results" : result
        }

    @schema_tool
    async def run_code_interpreter(
    ):
        """Run hypothesis testing on files generated from an experiment"""

        out_dir = "/Users/gkreder/Downloads/2024-07-23_greedy-set"
        file_descriptions_fname = os.path.join(out_dir, "file_descriptions.json")
        hypotheses_fname = os.path.join(out_dir, "hypotheses.json")
        
        # Generate the file descriptions
        data_dir = "/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3"
        files = ["/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/a_live_mtbl3_metabolite profiling_mass spectrometry.txt",
                 "/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/i_Investigation.txt",
                 "/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/m_live_mtbl3_metabolite profiling_mass spectrometry_v2_maf.tsv",
                 "/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/s_live_mtbl3.txt"]
        file_explorer = Role(
            name = "File Explorer",
            instructions = "You are a file explorer. You read given files generated by scientific experiments to get a sense of their content and structure",
            constraints = None,
            register_default_events = True,
            model = CONFIG['llm_model']
        )
        files_string = '\n'.join(files)
        file_descriptions = await file_explorer.acall(
            [
                f"Explore the following files to get a sense of their content and structure using the Python pandas and built-in libraries. Keep in mind that these files are generated from a scientific study and your job is to understand their content and structure.",
                f"Files:\n```{files_string}```",
            ],
            tools=[run_code],
            output_schema=FileDescriptions,
        )
        with open(file_descriptions_fname, 'w') as f:
            json.dump(file_descriptions.dict(), f, indent=4)

        
        # # Generate hypotheses
        file_descriptions = FileDescriptions(**json.loads(open(file_descriptions_fname, 'r').read()))
        hypothesizer = Role(
            name = "Data Hypothesizer",
            instructions = "You are a data hypothesizer. Based on the file descriptions, generate hypotheses that can be tested about the data generated from a scientific study. Limit yourself to at most 5 hypotheses (less if you cannot think of 5 testable hypotheses)",
            constraints = None,
            register_default_events = True,
            model = CONFIG['llm_model']
        )

        hypotheses = await hypothesizer.aask(["Take the following file descriptions of files generated from a scientific study and generate hypotheses that can be tested using Python about the data generated from the study.", file_descriptions], output_schema=DataHypotheses)
        with open(hypotheses_fname, 'w') as f:
            json.dump(hypotheses.dict(), f, indent=4)
        hypotheses = DataHypotheses(**json.loads(open(hypotheses_fname, 'r').read()))


        # Generate hypothesis testing code
        code_generator = Role(
            name = "Hypothesis Code Generator",
            instructions = """You are a hypothesis tester. You explore files and write code to test hypotheses on the data generated from a scientific study.""",
            constraints = None,
            register_default_events = True,
            model = CONFIG['llm_model']
        )

        hypothesis_plans = [
                code_generator.aask(
                ["""Take this hypothesis and descriptions of available files and make a code outline for how you would test the hypothesis on the data files generated from a scientific study
                Do not write actual code, rather write a series of steps in plain text that the code would perform.
                """,
                hypothesis,
                file_descriptions,
                ]
                )
                for hypothesis in hypotheses.hypotheses]
        hypothesis_plans = await asyncio.gather(*hypothesis_plans)

        file_description_codes = [
                code_generator.acall([
                f"""Take the following hypothesis, hypothesis testing plan, and high-level descriptions of available files and generate an ultra-detailed understanding of the file contents from a coder's point of view.
                Use the `run_code` tool as many time as necessary to explore the files - for example understanding structure, columns, row values, etc.
                Use this to write a more detailed description of the file contents with the specific information needed to test the hypothesis according to the plan.
                For example, if the plan calls for grouping samples by a certain factor, you should describe the relevant columns and the values they contain that would be used to group the samples.
                The files are available in the directory {data_dir}
                """,
                hypotheses.hypotheses[i],
                hypothesis_plans[i],
                file_descriptions,
            ],
            tools = [run_code],
            max_loop_count = 25)
            # for i in range(len(hypotheses.hypotheses))]
            for i in [0]]
        file_description_codes = await asyncio.gather(*file_description_codes)
        # ipdb.set_trace()

        analyses = [
                code_generator.acall([
                f"""Take the following hypothesis, hypothesis testing plan, and ultra-detailed descriptions of available files.
                Use the `run_code` tool to test the hypothesis, creating all necessary visualizations and output files in the process.
                Make sure to use the files correctly by double-checking keys, columns, etc that you reference.
                Your final output should include the functioning Python code that you used as well as references to any output files generated.
                The files are available in the directory {data_dir}
                """,
                hypotheses.hypotheses[i],
                file_descriptions,
                file_description_codes[i],
            ],
            tools = [run_code],
            max_loop_count = 25)
            for i in [0]]
        analyses = await asyncio.gather(*analyses)
        for i_analysis, analysis in enumerate(analyses):
            with open(f"analyses_{i_analysis}.txt", 'w') as f:
                print(analysis, file=f)
        

        return {
            "results" : data_store,
            "analyses" : analyses
        }
    return run_code_interpreter

async def main():
    data_store = HyphaDataStore()
    data_analyst = create_analyzer_function(data_store=data_store)
    result = await data_analyst()


if __name__ == "__main__":
    # asyncio.run(main())
    # asyncio.run("0.0.0.0")
    asyncio.run(main())