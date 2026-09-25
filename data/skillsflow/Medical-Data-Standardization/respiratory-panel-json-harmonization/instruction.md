A respiratory monitoring export is stored as JSON instead of a flat CSV.

Inputs:
- `/root/environment/data/respiratory_panel.json`
- `/root/environment/data/respiratory_feature_descriptions.csv`

Create `/root/respiratory_panel_harmonized.csv`.

Requirements:
1. Read the JSON array under `panels`.
2. Keep only entries whose `status` is `final`.
3. Flatten each retained entry so the output columns are, in order: `pH_Arterial`, `pCO2_Arterial`, `pO2_Arterial`, `Bicarbonate`, `Lactate`, `Glucose`, `Magnesium`.
4. Drop any retained entry with a missing measurement after flattening.
5. Parse scientific notation into normal decimals and treat commas as decimal separators.
6. Detect alternate-unit values using plausible physiological ranges and convert them into US conventional units.
7. Round every output value to exactly 2 decimal places.
8. The final CSV must not contain identifiers, JSON metadata, blanks, commas, scientific notation, or unconverted out-of-range values.
