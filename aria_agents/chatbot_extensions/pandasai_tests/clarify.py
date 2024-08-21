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

query = """
How are the wild-type and delta-9 desaturase knockout strains identified in the datasets?


Save your results to files for future reference.
"""

# What statistical significance threshold should be used for the hypothesis testing?
# What specific columns in the dataframes correspond to the lipid metabolites that need to be analyzed?



response = agent.chat(query)
print("-----------------------------------")
print("Response")
print("-----------------------------------")
print(response)

print("-----------------------------------")
print("Clarification questions")
print("-----------------------------------")
questions = agent.clarification_questions(query)
for question in questions:
    print(f"\t{question}")

 
print("-----------------------------------")
print("Explanation")
print("-----------------------------------")
explanation = agent.explain()
print(explanation)


print("-----------------------------------")
print("Rephrased query")
print("-----------------------------------")
rephrased_query = agent.rephrase_query(query)





