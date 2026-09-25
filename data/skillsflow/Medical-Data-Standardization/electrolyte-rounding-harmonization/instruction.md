An electrolyte monitoring export needs the same harmonization workflow as the other panels, but the mix of columns is different.

Inputs:
- `/root/environment/data/electrolyte_rounding_panel.csv`
- `/root/environment/data/electrolyte_feature_descriptions.csv`

Create `/root/electrolyte_rounding_panel_harmonized.csv`.

Requirements:
1. Drop any row with a missing measurement.
2. Parse scientific notation into ordinary decimals and treat commas as decimal separators.
3. Detect alternate-unit values using plausible physiological ranges and convert them into US conventional units.
4. Round every value to exactly 2 decimal places using `X.XX` formatting.
5. Preserve the measurement column order from the source file and omit the identifier column.
6. The final file must not contain blanks, commas, scientific notation, or unconverted out-of-range values.

Unit conversion reference (to be inferred from out-of-range detection):
- Magnesium: 1 mmol/L ≈ 0.411 mg/dL (SI to US conventional). If a value is far above the normal range for mg/dL, treat it as mmol/L and convert.
- Calcium: 1 mmol/L ≈ 0.25 mg/dL (SI to US conventional). If a value is far above the normal range for mg/dL, treat it as mmol/L and convert.
- Glucose: 1 mmol/L ≈ 0.0555 mg/dL (SI to US conventional). If a value is far above the normal range for mg/dL, treat it as mmol/L and convert.
- Creatinine: 1 μmol/L ≈ 88.4 mg/dL (SI to US conventional). If a value is far above the normal range for mg/dL, treat it as μmol/L and convert.
