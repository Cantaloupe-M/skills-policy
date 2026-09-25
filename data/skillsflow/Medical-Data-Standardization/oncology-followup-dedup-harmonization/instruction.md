An oncology follow-up export contains repeated draws for the same case, and you only need the most recent complete draw per case.

Input files:
- `/root/environment/data/oncology_followup_panel.csv`
- `/root/environment/data/oncology_feature_descriptions.csv`

Create `/root/oncology_followup_panel_harmonized.csv`.

Requirements:
1. Group rows by `case_id`.
2. Keep only the highest `draw_order` row for each case that is complete across all measurements.
3. If a higher `draw_order` row is incomplete, fall back to the next-highest complete row for that same case.
4. Parse scientific notation into ordinary decimals and treat commas as decimal separators.
5. Detect alternate-unit values using plausible physiological ranges and convert them into US conventional units.
6. Round every output value to exactly 2 decimal places.
7. The output must contain one row per retained case, must omit `case_id` and `draw_order`, and must preserve the measurement column order from the source file.
8. The final file must not contain blanks, commas, scientific notation, duplicate cases, or unconverted out-of-range values.
