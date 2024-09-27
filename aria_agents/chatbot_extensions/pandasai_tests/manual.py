import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
file_path_a = '/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/a_live_mtbl3_metabolite profiling_mass spectrometry.txt'
file_path_m = '/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/m_live_mtbl3_metabolite profiling_mass spectrometry_v2_maf.tsv'
file_path_s = '/Users/gkreder/org/data/CC/4918D6-79F7-49FA-B79C-554D6A9452EC/sample_data/MTBLS3/s_live_mtbl3.txt'
data_a = pd.read_csv(file_path_a, sep='\t')
data_m = pd.read_csv(file_path_m, sep='\t')
data_s = pd.read_csv(file_path_s, sep='\t')
dfs = [data_a, data_m, data_s]
df_samples = dfs[0]
df_metabolites = dfs[1]
df_characteristics = dfs[2]

