A neonatal sepsis surveillance export uses mixed unit systems and inconsistent header names.

The source file is `/root/environment/data/neonatal_sepsis_panel.csv` and the column glossary is `/root/environment/data/neonatal_feature_descriptions.csv`.

Save the cleaned result to `/root/neonatal_sepsis_panel_harmonized.csv`.

Requirements:
1. Remove any row with a missing measurement.
2. Parse scientific notation into ordinary decimal numbers.
3. Treat commas as decimal separators.
4. Some columns have alternate-unit values mixed in. Detect them from physiologically implausible ranges and convert them into the conventional reporting units implied by the glossary.
5. Round every numeric value to exactly 2 decimal places.
6. The output must preserve the measurement columns in the same order as the input, but omit the identifier column.
7. Keep the original header names exactly as they appear in the source file.
8. The final file must not contain commas, scientific notation, empty cells, or out-of-range values that should have been converted.
