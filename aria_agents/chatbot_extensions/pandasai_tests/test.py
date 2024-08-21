import pandas as pd
from pandasai.llm import OpenAI
from pandasai import SmartDataframe, SmartDatalake, Agent

llm = OpenAI()


# Load the data from the specified files
file_path_a = '/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/a_live_mtbl3_metabolite profiling_mass spectrometry.txt'
file_path_m = '/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/m_live_mtbl3_metabolite profiling_mass spectrometry_v2_maf.tsv'
file_path_s = '/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/s_live_mtbl3.txt'

data_a = pd.read_csv(file_path_a, sep='\t')
data_m = pd.read_csv(file_path_m, sep='\t')
data_s = pd.read_csv(file_path_s, sep='\t')


# sdl = SmartDatalake([data_a, data_m, data_s], config = {'llm': llm})
# result = sdl.chat("Which metabolites have most significant differences between the gene knockout experimental conditions?")
# print(result)

agent = Agent([data_a, data_m, data_s], config = {'llm': llm}, memory_size=10)

# query = "Which metabolites have most significant differences between the gene knockout experimental conditions?"
# query = "Plot the metabolite average metabolite intensity for each metabolite in each experimental condition. Experimental conditions are indicates by `Factor Value[gene knockout]`"
# query = "Plot the average metabolite intensities for each metabolite in each experimental condition separating between intensities in wild type and non wild type. Experimental conditions are indicated by `Factor Value[gene knockout]`."
query = """
Explore the dataframes to get a sense of their content and structure. Keep in mind that these files are generated from a scientific study and your job is to understand their content and structure.
Generate a detailed textual description of the file set and the underlying study they may have come from. Include things like samples, experimental conditions, and any other relevant information that could be used to test hypotheses on the dataframes.

Save your results to a file
"""


response = agent.chat(query)
print(response)
print("-----------------------------------")

questions = agent.clarification_questions(query)
for question in questions:
    print(f"\t{question}")
print("-----------------------------------")

explanation = agent.explain()
print(explanation)


