from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import pandas as pd

from harmonize import normalize_frame

main = pd.read_csv('/root/environment/data/metabolic_main.csv', dtype=str)
extra = pd.read_csv('/root/environment/data/metabolic_additional.csv', dtype=str)
specs = {'Sodium': ('same', 1.0, 110, 170), 'Potassium': ('same', 1.0, 2.0, 8.5), 'Chloride': ('same', 1.0, 70, 140), 'Bicarbonate': ('same', 1.0, 5, 40), 'Glucose': ('single', 0.0555, 20, 800), 'Lactate': ('single-reverse', 9.01, 0.3, 20), 'Calcium': ('single', 0.25, 5.0, 15.0), 'Magnesium': ('single', 0.411, 0.5, 10.0), 'Phosphorus': ('single', 0.323, 1.0, 15.0), 'Creatinine': ('single', 88.4, 0.2, 20), 'BUN': ('single', 0.357, 5, 200), 'Anion_Gap': ('same', 1.0, 0, 40), 'Osmolality': ('same', 1.0, 200, 450), 'Beta_Hydroxybutyrate': ('single', 10.4, 0, 15), 'pH_Arterial': ('same', 1.0, 6.8, 7.8), 'pCO2_Arterial': ('single', 0.133, 15, 100)}
main_clean = normalize_frame(main, {k: specs[k] for k in main.columns if k != 'record_id'}, id_column='record_id')
extra_clean = normalize_frame(extra, {k: specs[k] for k in extra.columns if k != 'record_id'}, id_column='record_id')
merged = main_clean.merge(extra_clean, on='record_id', how='inner')
merged[['Sodium', 'Potassium', 'Chloride', 'Bicarbonate', 'Glucose', 'Lactate', 'Calcium', 'Magnesium', 'Phosphorus', 'Creatinine', 'BUN', 'Anion_Gap', 'Osmolality', 'Beta_Hydroxybutyrate', 'pH_Arterial', 'pCO2_Arterial']].to_csv('/root/icu_metabolic_panel_harmonized.csv', index=False)
