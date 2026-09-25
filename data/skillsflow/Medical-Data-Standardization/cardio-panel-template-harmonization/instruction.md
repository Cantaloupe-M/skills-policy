A cardiology workflow already created an output template file, and you need to replace it with harmonized data instead of creating a differently named file.

Inputs:
- `/root/environment/data/cardiology_panel.csv`
- `/root/environment/data/cardiology_feature_descriptions.csv`
- `/root/environment/data/cardiology_output_template.csv`

Required output path:
- `/root/cardiology_output_template.csv`

Requirements:
1. Start from the measurements in `cardiology_panel.csv`.
2. Drop any row with a missing measurement.
3. Parse scientific notation into normal decimals and treat commas as decimal separators.
4. Detect alternate-unit values using plausible physiological ranges and convert them into US conventional units.
5. Round every output value to exactly 2 decimal places.
6. Write the final harmonized data to `/root/cardiology_output_template.csv` using the exact header order from the provided template.
7. Do not keep the identifier column.
8. The final file must not contain placeholder text, blanks, commas, scientific notation, or unconverted out-of-range values.

Unit conversion reference (apply when a value is out of the US conventional range):
- BNP: 1 pmol/L ≈ 0.289 pg/mL.
- NT_proBNP: 1 pmol/L ≈ 0.118 pg/mL.
- Troponin_I: 1 μg/L ≈ 1000 ng/mL.
- Troponin_T: 1 μg/L ≈ 1000 ng/mL.
- Creatinine: 1 μmol/L ≈ 88.4 mg/dL.
- Magnesium: 1 mmol/L ≈ 0.411 mg/dL.
