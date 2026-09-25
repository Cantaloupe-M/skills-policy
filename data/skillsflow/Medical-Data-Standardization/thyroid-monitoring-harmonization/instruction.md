A thyroid clinic exported follow-up labs from different analyzers, and the units are inconsistent.

Use `/root/environment/data/thyroid_monitoring_panel.csv` as the source data and `/root/environment/data/thyroid_feature_descriptions.csv` for column meanings.

Create a cleaned file at `/root/thyroid_monitoring_panel_harmonized.csv`.

Requirements:
1. Remove any row with a missing measurement.
2. Normalize number formatting: parse scientific notation, and treat commas as decimal separators.
3. For each measurement, values outside a plausible physiological range should be treated as alternate-unit values and converted into the conventional unit used by the clinic.
4. Format every output number with exactly 2 decimal places.
5. Preserve the measurement column order from the input and omit the identifier column from the output.
6. The output must contain only complete rows and must not contain commas, scientific notation, or unconverted out-of-range values.

Unit conversion reference (apply when a value is out of the US conventional range):
- Free_T4: 1 pmol/L ≈ 12.87 ng/dL.
- Free_T3: 1 pmol/L ≈ 15.38 pg/dL.
- Total_T4: 1 nmol/L ≈ 12.87 μg/dL.
- Total_T3: 1 nmol/L ≈ 0.0154 ng/dL.
- Calcium: 1 mmol/L ≈ 0.25 mg/dL.
- Phosphorus: 1 mmol/L ≈ 0.323 mg/dL.
- Magnesium: 1 mmol/L ≈ 0.411 mg/dL.
- PTH: 1 pmol/L ≈ 0.106 pg/mL.
- Vitamin_D_25OH: 1 nmol/L ≈ 2.5 ng/mL.
- Creatinine: 1 μmol/L ≈ 88.4 mg/dL.
