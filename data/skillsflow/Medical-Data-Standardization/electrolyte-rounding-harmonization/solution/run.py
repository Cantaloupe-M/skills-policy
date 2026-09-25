from pathlib import Path
import sys

sys.path.insert(0, str((Path(__file__).resolve().parent / "tools").resolve()))

import pandas as pd

from harmonize import normalize_frame

data_dir = Path('/root/environment/data')

df = pd.read_csv(data_dir / 'electrolyte_rounding_panel.csv', dtype=str)
specs = {'Sodium': ('same', 1.0, 110, 170), 'Potassium': ('same', 1.0, 2.0, 8.5), 'Chloride': ('same', 1.0, 70, 140), 'Bicarbonate': ('same', 1.0, 5, 40), 'Magnesium': ('single', 0.411, 0.5, 10), 'Calcium': ('single', 0.25, 5.0, 15.0), 'Glucose': ('single', 0.0555, 20, 800), 'Creatinine': ('single', 88.4, 0.2, 20)}
clean = normalize_frame(df, specs, id_column='encounter_id')
clean[['Sodium', 'Potassium', 'Chloride', 'Bicarbonate', 'Magnesium', 'Calcium', 'Glucose', 'Creatinine']].to_csv('/root/electrolyte_rounding_panel_harmonized.csv', index=False)
