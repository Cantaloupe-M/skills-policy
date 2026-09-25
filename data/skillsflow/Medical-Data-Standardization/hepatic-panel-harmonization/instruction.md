You are cleaning a hepatology lab export that was merged from multiple hospitals.

The input file is `/root/environment/data/hepatic_lab_panel.csv`. Field meanings are listed in `/root/environment/data/hepatic_feature_descriptions.csv`.

Please normalize the dataset and save the final CSV to `/root/hepatic_lab_panel_harmonized.csv`.

Requirements:
1. Drop any patient row that contains a missing or empty measurement.
2. Convert scientific notation such as `1.23e2` into normal numeric form.
3. Interpret commas as decimal separators when present.
4. Some measurements are reported in alternate units. Detect those by checking whether a value falls outside a plausible physiological range for that measurement, then convert it into US conventional units.
5. Round every numeric value to exactly 2 decimal places using `X.XX` formatting.
6. The output must keep the same measurement columns and column order as the input, except do not include the identifier column.
7. The final file must not contain scientific notation, commas, blank cells, or mixed-unit values.

Unit conversion reference (apply when a value is out of the US conventional range):
- Total_Bilirubin: 1 μmol/L ≈ 17.1 mg/dL (SI to US).
- Direct_Bilirubin: 1 μmol/L ≈ 17.1 mg/dL.
- Albumin: 1 g/L ≈ 10.0 g/dL.
- Total_Protein: 1 g/L ≈ 10.0 g/dL.
- Ammonia: 1 μmol/L ≈ 0.587 μg/dL.
- Creatinine: 1 μmol/L ≈ 88.4 mg/dL.
- Hemoglobin: 1 g/L ≈ 10.0 g/dL.
- Ferritin: 1 pmol/L ≈ 2.247 μg/L.
- Glucose: 1 mmol/L ≈ 0.0555 mg/dL.
