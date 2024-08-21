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
query = "Plot the average intensities for each metabolite in wild type versus Delta 9 fat 6 samples. Sample conditions are indicated by `Factor Value[Sample Type]`."
query = """Here are the descriptions of dataframes that you've been equipped with:

```The data files have been successfully loaded and their structures have been examined. Here is a detailed understanding of the file contents from a coder's point of view:

1. **a_data**:
   - This file contains data related to metabolite profiling using mass spectrometry.
   - It has 35 columns, including 'Sample Name', 'Protocol REF', 'Parameter Value[Post Extraction]', 'Parameter Value[Derivatization]', 'Extract Name', 'Parameter Value[Chromatography Instrument]', 'MS Assay Name', 'Raw Spectral Data File', 'Normalization Name', 'Derived Spectral Data File', and 'Metabolite Assignment File'.
   - The data includes various parameters related to the mass spectrometry process and the resulting metabolite assignments.

2. **m_data (m_live_mtbl3_metabolite profiling_mass spectrometry_v2_maf.tsv)**:
   - This file contains tabular data with columns representing database identifiers, chemical formulas, and various sample measurements.
   - It has 84 columns, including 'database_identifier', 'chemical_formula', 'smiles', 'inchi', 'metabolite_identification', 'mass_to_charge', 'fragmentation', 'charge', 'retention_time', and multiple columns for sample measurements (e.g., 'Cecilia_AA_rerun05', 'Cecilia_AA_rerun06', etc.).
   - The data includes detailed information about each metabolite and its abundance in different samples.

3. **s_data**:
   - This file contains data related to the study samples, including source names, organism characteristics, protocol references, sample names, and factor values.
   - It has 12 columns, including 'Source Name', 'Characteristics[Organism]', 'Characteristics[Organism part]', 'Protocol REF', 'Sample Name', 'Factor Value[gene knockout]'.
   - The data includes metadata about each sample, such as the organism used, the part of the organism, and whether the sample is from a knockout strain or a wild-type strain.

This detailed understanding of the file contents will be used to test the hypothesis according to the plan. The next steps involve parsing the data, filtering lipid metabolites, grouping data by strain type, performing statistical analysis, adjusting for multiple comparisons, creating visualizations, and interpreting the results.```

And here's a hypothesis to test based on the files together with a brief justification of it:

```
hypothesis='Delta-9 desaturase knockout strains of Caenorhabditis elegans show a significant difference in lipid metabolite abundance compared to wild-type strains.' justification="The study aims to understand the regulation of lipid content by delta-9 desaturases. Identify columns corresponding to wild-type and delta-9 desaturase knockout strains. 3. Perform statistical tests (e.g., t-tests) to compare the abundance of lipid metabolites between the two groups. 4. Correct for multiple comparisons using the Benjamini-Hochberg procedure." visualization='Create box plots and volcano plots to visualize the differences in lipid metabolite abundance between wild-type and knockout strains.'
```

Now test the hypothesis using the dataframe information
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


