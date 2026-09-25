A transplant monitoring panel is split across two lab exports with semantically related but not identical record keys.

Inputs:
- `/root/environment/data/transplant_chemistry.csv`
- `/root/environment/data/transplant_liver.csv`
- `/root/environment/data/transplant_feature_descriptions.csv`

Create `/root/transplant_panel_harmonized.csv`.

Requirements:
1. Align rows using `patient_code`. Ignore `visit_tag` after alignment.
2. Keep only patients that appear in both source files.
3. Drop any aligned patient whose combined measurements are incomplete.
4. Parse scientific notation into normal decimals and treat commas as decimal separators.
5. Detect alternate-unit values using plausible physiological ranges and convert them into US conventional units.
6. Round every output value to exactly 2 decimal places.
7. The output must contain only measurement columns, in this order: first all columns from `transplant_chemistry.csv` after `patient_code`, then all columns from `transplant_liver.csv` after `patient_code` and `visit_tag`.
8. The final file must not contain identifiers, blanks, commas, scientific notation, or unconverted out-of-range values.
