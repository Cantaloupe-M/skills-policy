from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import json

import pandas as pd

from harmonize import normalize_frame

with open('/root/environment/data/respiratory_panel.json') as handle:
    raw = json.load(handle)['panels']

rows = []
for entry in raw:
    if entry['status'] != 'final':
        continue
    rows.append({
        'sample_id': entry['sample_id'],
        'pH_Arterial': entry['measurements']['acid_base']['pH_Arterial'],
        'pCO2_Arterial': entry['measurements']['acid_base']['pCO2_Arterial'],
        'pO2_Arterial': entry['measurements']['acid_base']['pO2_Arterial'],
        'Bicarbonate': entry['measurements']['acid_base']['Bicarbonate'],
        'Lactate': entry['measurements']['metabolic']['Lactate'],
        'Glucose': entry['measurements']['metabolic']['Glucose'],
        'Magnesium': entry['measurements']['metabolic']['Magnesium'],
    })

df = pd.DataFrame(rows)
specs = {'pH_Arterial': ('same', 1.0, 6.8, 7.8), 'pCO2_Arterial': ('single', 0.133, 15, 100), 'pO2_Arterial': ('single', 0.133, 30, 500), 'Bicarbonate': ('same', 1.0, 5, 40), 'Lactate': ('single-reverse', 9.01, 0.3, 20), 'Glucose': ('single', 0.0555, 20, 800), 'Magnesium': ('single', 0.411, 0.5, 10)}
clean = normalize_frame(df, specs, id_column='sample_id')
clean[['pH_Arterial', 'pCO2_Arterial', 'pO2_Arterial', 'Bicarbonate', 'Lactate', 'Glucose', 'Magnesium']].to_csv('/root/respiratory_panel_harmonized.csv', index=False)
