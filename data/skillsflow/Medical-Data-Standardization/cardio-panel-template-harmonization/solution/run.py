from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))

import pandas as pd

from harmonize import normalize_frame

df = pd.read_csv('/root/environment/data/cardiology_panel.csv', dtype=str)
template_cols = list(pd.read_csv('/root/environment/data/cardiology_output_template.csv', nrows=0).columns)
specs = {'BNP': ('single', 0.289, 0, 5000), 'NT_proBNP': ('single', 0.118, 0, 35000), 'Troponin_I': ('single', 1000, 0, 50), 'Troponin_T': ('single', 1000, 0, 10), 'Creatinine': ('single', 88.4, 0.2, 20), 'Sodium': ('same', 1.0, 110, 170), 'Potassium': ('same', 1.0, 2.0, 8.5), 'Magnesium': ('single', 0.411, 0.5, 10)}
clean = normalize_frame(df, specs, id_column='encounter_id')
clean[template_cols].to_csv('/root/cardiology_output_template.csv', index=False)
