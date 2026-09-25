from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import pandas as pd

from harmonize import normalize_frame

df = pd.read_csv('/root/environment/data/thyroid_monitoring_panel.csv', dtype=str)
specs = {'TSH': ('same', 1.0, 0.01, 150), 'Free_T4': ('single', 12.87, 0.2, 6.0), 'Free_T3': ('single', 1.536, 1.0, 10.0), 'Total_T4': ('single', 12.87, 1.0, 24.0), 'Total_T3': ('single', 0.0154, 20, 600), 'Anti_TPO': ('same', 1.0, 0, 5000), 'Thyroglobulin': ('same', 1.0, 0.1, 5000), 'Thyroglobulin_Antibody': ('same', 1.0, 0, 4000), 'Calcium': ('single', 0.25, 5.0, 15.0), 'Ionized_Calcium': ('single', 4.0, 0.8, 2.0), 'Phosphorus': ('single', 0.323, 1.0, 15.0), 'Magnesium': ('single', 0.411, 0.5, 10.0), 'PTH': ('single', 0.106, 5, 2500), 'Vitamin_D_25OH': ('single', 2.496, 4, 200), 'Calcitonin': ('same', 1.0, 0, 500), 'Creatinine': ('single', 88.4, 0.2, 20)}
clean = normalize_frame(df, specs, id_column='encounter_id')
clean[['TSH', 'Free_T4', 'Free_T3', 'Total_T4', 'Total_T3', 'Anti_TPO', 'Thyroglobulin', 'Thyroglobulin_Antibody', 'Calcium', 'Ionized_Calcium', 'Phosphorus', 'Magnesium', 'PTH', 'Vitamin_D_25OH', 'Calcitonin', 'Creatinine']].to_csv('/root/thyroid_monitoring_panel_harmonized.csv', index=False)
