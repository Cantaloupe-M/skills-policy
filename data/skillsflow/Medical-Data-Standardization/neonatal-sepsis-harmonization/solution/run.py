from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import pandas as pd

from harmonize import normalize_frame

df = pd.read_csv('/root/environment/data/neonatal_sepsis_panel.csv', dtype=str)
specs = {'CRP_mg_L_or_mg_dL': ('single-reverse', 0.1, 0, 50), 'Serum_Creat_umol_or_mgdl': ('single', 88.4, 0.2, 20), 'BUN_mmol_or_mgdl': ('single', 0.357, 5, 200), 'Glucose_mmol_or_mgdl': ('single', 0.0555, 20, 800), 'Total_Bili_umol_or_mgdl': ('single', 17.1, 0.1, 30), 'Direct_Bili_umol_or_mgdl': ('single', 17.1, 0.0, 15), 'Lactate_mgdl_or_mmol': ('single-reverse', 9.01, 0.3, 20), 'Platelet_Count': ('same', 1.0, 10, 1500), 'WBC_Count': ('same', 1.0, 0.5, 50), 'Hemoglobin_gL_or_gdL': ('single', 10.0, 3, 20), 'Sodium': ('same', 1.0, 110, 170), 'Potassium': ('same', 1.0, 2.0, 8.5), 'pCO2_kPa_or_mmHg': ('single', 0.133, 15, 100)}
clean = normalize_frame(df, specs, id_column='specimen_id')
clean[['CRP_mg_L_or_mg_dL', 'Serum_Creat_umol_or_mgdl', 'BUN_mmol_or_mgdl', 'Glucose_mmol_or_mgdl', 'Total_Bili_umol_or_mgdl', 'Direct_Bili_umol_or_mgdl', 'Lactate_mgdl_or_mmol', 'Platelet_Count', 'WBC_Count', 'Hemoglobin_gL_or_gdL', 'Sodium', 'Potassium', 'pCO2_kPa_or_mmHg']].to_csv('/root/neonatal_sepsis_panel_harmonized.csv', index=False)
