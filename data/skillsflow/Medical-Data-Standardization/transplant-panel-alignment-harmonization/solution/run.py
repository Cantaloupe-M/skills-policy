from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import pandas as pd

from harmonize import normalize_frame

left = pd.read_csv('/root/environment/data/transplant_chemistry.csv', dtype=str)
right = pd.read_csv('/root/environment/data/transplant_liver.csv', dtype=str)
merged = left.merge(right.drop(columns=['visit_tag']), on='patient_code', how='inner')
specs = {'Tacrolimus': ('single', 1.277, 1, 40), 'Creatinine': ('single', 88.4, 0.2, 20), 'Magnesium': ('single', 0.411, 0.5, 10), 'Potassium': ('same', 1.0, 2.0, 8.5), 'Glucose': ('single', 0.0555, 20, 800), 'Bilirubin_Total': ('single', 17.1, 0.1, 30), 'Albumin': ('single', 10.0, 1.0, 6.5), 'AST': ('same', 1.0, 5, 2000), 'ALT': ('same', 1.0, 5, 2000), 'Phosphorus': ('single', 0.323, 1.0, 15)}
clean = normalize_frame(merged, specs, id_column='patient_code')
clean[['Tacrolimus', 'Creatinine', 'Magnesium', 'Potassium', 'Glucose', 'Bilirubin_Total', 'Albumin', 'AST', 'ALT', 'Phosphorus']].to_csv('/root/transplant_panel_harmonized.csv', index=False)
