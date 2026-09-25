from pathlib import Path
import sys

sys.path.insert(0, str((Path(__file__).resolve().parent / "tools").resolve()))

import pandas as pd

from harmonize import normalize_frame

data_dir = Path('/root/environment/data')

df = pd.read_csv(data_dir / 'hepatic_lab_panel.csv', dtype=str)
specs = {'AST': ('same', 1.0, 5, 2000), 'ALT': ('same', 1.0, 5, 2000), 'ALP': ('same', 1.0, 20, 2000), 'GGT': ('same', 1.0, 5, 2500), 'Total_Bilirubin': ('single', 17.1, 0.1, 30), 'Direct_Bilirubin': ('single', 17.1, 0.0, 15), 'Albumin': ('single', 10.0, 1.0, 6.5), 'Total_Protein': ('single', 10.0, 3.0, 12.0), 'INR': ('same', 1.0, 0.8, 12.0), 'Ammonia': ('single', 0.587, 10, 400), 'Platelets': ('same', 1.0, 10, 1500), 'AFP': ('same', 1.0, 0.5, 200000), 'Bile_Acids': ('same', 1.0, 0.5, 400), 'Creatinine': ('single', 88.4, 0.2, 20), 'Sodium': ('same', 1.0, 110, 170), 'Hemoglobin': ('single', 10.0, 3, 20), 'Ferritin': ('single', 2.247, 5, 5000), 'Glucose': ('single', 0.0555, 20, 800)}
clean = normalize_frame(df, specs, id_column='patient_id')
clean[['AST', 'ALT', 'ALP', 'GGT', 'Total_Bilirubin', 'Direct_Bilirubin', 'Albumin', 'Total_Protein', 'INR', 'Ammonia', 'Platelets', 'AFP', 'Bile_Acids', 'Creatinine', 'Sodium', 'Hemoglobin', 'Ferritin', 'Glucose']].to_csv('/root/hepatic_lab_panel_harmonized.csv', index=False)
