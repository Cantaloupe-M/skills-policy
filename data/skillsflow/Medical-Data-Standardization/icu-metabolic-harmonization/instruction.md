An ICU metabolic panel was split across two source files from different systems.

Inputs:
- `/root/environment/data/metabolic_main.csv`
- `/root/environment/data/metabolic_additional.csv`
- `/root/environment/data/metabolic_feature_descriptions.csv` for column meanings

Produce a single harmonized CSV at `/root/icu_metabolic_panel_harmonized.csv`.

Requirements:
1. Join the two source files by `record_id`.
2. Drop any joined record that contains a missing or empty measurement in either source file.
3. Parse scientific notation into normal numeric form.
4. Treat commas as decimal separators.
5. Some measurements use alternate units; detect those by checking whether a value is outside a plausible physiological range for that measurement, then convert it into US conventional units.
6. Round every measurement to exactly 2 decimal places using `X.XX` formatting.
7. The output must contain only the measurement columns, not `record_id`.
8. The output column order must be: first all measurement columns from `metabolic_main.csv` after `record_id`, then all measurement columns from `metabolic_additional.csv` after `record_id`.
9. The final file must not contain scientific notation, commas, or blank cells.
