
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

agent = Agent([data_a, data_m, data_s], config = {'llm': llm}, memory_size=10)

query = """DataFrame 0 contains 63 samples and 35 parameters related to the experimental setup.
Each row represents a sample with the following key columns:
- Sample Name: Identifier for each sample (e.g., 'Cecilia_AA_batch23_43').
- Protocol REF: Indicates the protocol used for extraction or analysis.
- Parameter Value[Post Extraction]: Describes the state of the sample after extraction.
- Parameter Value[Derivatization]: Details on any derivatization process applied.
- Extract Name: Name of the extract derived from the sample.
- Instrument details: Information about the chromatography and mass spectrometry instruments used (e.g., 'Thermo Electron TRACE GC Ultra').
- Scan polarity and m/z range: Settings for mass spectrometry analysis.
- Raw Spectral Data File: Path to the raw data file generated during analysis.
- Derived Spectral Data File: Path to the transformed data file for further analysis.
- Metabolite Assignment File: File containing metabolite identification results.

This DataFrame likely pertains to a study focused on metabolomics, analyzing various metabolites extracted from biological samples, specifically from the organism Caenorhabditis elegans.

DataFrame 1 contains 22 metabolites identified across 84 parameters.
Key columns include:
- database_identifier: Unique identifier for the metabolite (e.g., 'CHEBI:18257').
- chemical_formula: Chemical formula of the metabolite (e.g., 'C5H9NO2').
- smiles: SMILES representation of the chemical structure.
- inchi: IUPAC International Chemical Identifier.
- metabolite_identification: Name of the metabolite (e.g., 'Thioproline').
- mass_to_charge: Mass-to-charge ratio observed in the analysis.
- retention_time: Time taken for the metabolite to elute during chromatography.
- taxid and species: Taxonomic information indicating the source organism (Caenorhabditis elegans).
- smallmolecule_abundance_sub: Abundance measurements for various runs.

This DataFrame provides insights into the metabolites present in the samples and their relative abundances, which can be used to assess metabolic changes under different experimental conditions.

DataFrame 2 contains 63 samples and 12 characteristics.
Key columns include:
- Source Name: Identifier for the source of the sample.
- Characteristics[Organism]: Organism from which the sample was derived (e.g., 'Caenorhabditis elegans').
- Characteristics[Organism part]: Part of the organism sampled (e.g., 'whole organism').
- Sample Name: Identifier for each sample.
- Factor Value[gene knockout]: Information on any genetic modifications applied to the samples.

This DataFrame provides contextual information about the samples, including genetic modifications and the specific parts of the organism analyzed, which is crucial for understanding the biological implications of the metabolomic data."""


response = agent.chat(query)
print(response)
print("-----------------------------------")

questions = agent.clarification_questions(query)
for question in questions:
    print(f"\t{question}")
print("-----------------------------------")

explanation = agent.explain()
print(explanation)