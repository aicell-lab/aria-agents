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

agent_config = {
    'llm': llm,
    'save_charts' : True,
    'save_charts_path' : "/Users/gkreder/Downloads/pai_charts",
    'open_charts' : True,
    'max_retries' : 10 # defaults is 3
}
agent = Agent([data_a, data_m, data_s], config = agent_config, memory_size=10)

# query = "Which metabolites have most significant differences between the gene knockout experimental conditions?"
# query = "Plot the metabolite average metabolite intensity for each metabolite in each experimental condition. Experimental conditions are indicates by `Factor Value[gene knockout]`"
# query = "Plot the average metabolite intensities for each metabolite in each experimental condition separating between intensities in wild type and non wild type. Experimental conditions are indicated by `Factor Value[gene knockout]`."
query = """
Explore the dataframes to get a sense of their content and structure. Keep in mind that these files are generated from a scientific study and your job is to understand their content and structure.
Generate a detailed textual description of the file set and the underlying study they may have come from. Include things like samples, experimental conditions, and any other relevant information that could be used to test hypotheses on the dataframes.

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

print("\n"*20)

query_2 = """
Now use your descriptions of the dataframe to generate a hypothesis that can be tested using the dataframes.
Do not test the hypothesis, rather return a detailed textual description of the hypothesis, your justification, and the specific row/column values that will be relevant.
Be very detailed in your description of the row values so that functioning code can be written from your description.
"""

response_2 = agent.chat(query_2)
print("-----------------------------------")
print("Response 2")
print("-----------------------------------")
print(response_2)


query_3 = """
Take your hypothesis and the descriptions of the dataframes and do another round of exploratory investigation on the dataframes to completely understand their content relevant to the hypothesis.
If there are categorical variables, make sure to understand the possible category values.
Do not test the hypothesis. Rather produce an updated ultra-detailed textual description of the dataframes that includes ALL the relevant information for the hypothesis, focusing on row/column values you will need to use and how you will use them.
"""

print("\n"*20)
response_3 = agent.chat(query_3)
print("-----------------------------------")
print("Response 3")
print("-----------------------------------")
print(response_3)



query_4 = """
Take your hypothesis and the descriptions of the dataframes and carry out the hypothesis testing.
Your results should be communicated in the form of a visualization
"""

print("\n"*20)
response_4 = agent.chat(query_4)
print("-----------------------------------")
print("Response 4")
print("-----------------------------------")
print(response_4)
print("-----------------------------------")
print("Explanation")
print("-----------------------------------")
explanation = agent.explain()
print(explanation)




