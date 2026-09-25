from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import pandas as pd

from harmonize import normalize_frame

df = pd.read_csv('/root/environment/data/oncology_followup_panel.csv', dtype=str)
numeric_cols = ['LDH', 'Uric_Acid', 'Creatinine', 'Phosphorus', 'Calcium', 'Albumin', 'Glucose', 'Magnesium', 'Potassium', 'WBC_Count']


def is_complete(row):
    for column in numeric_cols:
        value = str(row[column]).strip()
        if value == '' or value.lower() == 'nan':
            return False
    return True


df['draw_order_num'] = df['draw_order'].astype(int)
chosen = []
for _, group in df.groupby('case_id'):
    group = group.sort_values('draw_order_num', ascending=False)
    for _, row in group.iterrows():
        if is_complete(row):
            chosen.append(row.drop(labels=['draw_order_num']))
            break

picked = pd.DataFrame(chosen)
specs = {'LDH': ('same', 1.0, 80, 2500), 'Uric_Acid': ('single', 59.48, 1.0, 20.0), 'Creatinine': ('single', 88.4, 0.2, 20.0), 'Phosphorus': ('single', 0.323, 1.0, 15.0), 'Calcium': ('single', 0.25, 5.0, 15.0), 'Albumin': ('single', 10.0, 1.0, 6.5), 'Glucose': ('single', 0.0555, 20, 800), 'Magnesium': ('single', 0.411, 0.5, 10.0), 'Potassium': ('same', 1.0, 2.0, 8.5), 'WBC_Count': ('same', 1.0, 0.5, 50)}
clean = normalize_frame(picked, specs, id_column='case_id', keep_columns=list(specs))
clean[['LDH', 'Uric_Acid', 'Creatinine', 'Phosphorus', 'Calcium', 'Albumin', 'Glucose', 'Magnesium', 'Potassium', 'WBC_Count']].to_csv('/root/oncology_followup_panel_harmonized.csv', index=False)
