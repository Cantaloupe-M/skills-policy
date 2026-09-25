Read the part specifications from `/root/part_specifications.pdf` and inspection records from `/root/inspection_records.xlsx`, then create a new report called `/root/quality_report.xlsx`.

The part specifications PDF contains a table with columns: PART_ID, PART_NAME, LINE, TOLERANCE_MM, TARGET_WEIGHT. Note: the PDF may contain additional summary or reference tables beyond the main specifications table — only extract the row-level part data where PART_ID is a numeric identifier.

The inspection records XLSX contains columns: INSPECTION_ID, PART_ID, MEASUREMENT_MM, ACTUAL_WEIGHT, INSPECTOR, SHIFT, PASS_FAIL. Some rows may have missing values in MEASUREMENT_MM or ACTUAL_WEIGHT — keep these rows but treat missing numeric values as not available when computing derived columns.

Join the two datasets on PART_ID. Then create a new Excel file with four pivot table sheets and one source data sheet (five sheets total):

1. "Fail Rate by Line"
This sheet contains a pivot table with:
Rows: LINE
Values: Count (number of inspection records — count all records including Pass, Fail, and Inconclusive)

2. "Avg Deviation by Line"
This sheet contains a pivot table with:
Rows: LINE
Values: Average of DEVIATION_MM (see SourceData enrichment below)

3. "Inspections by Shift"
This sheet contains a pivot table with:
Rows: SHIFT
Values: Count (number of inspection records)

4. "Line Shift Matrix"
This sheet contains a pivot table with:
Rows: LINE
Columns: SHIFT
Values: Count (number of inspection records)

5. "SourceData"
This sheet contains the joined data enriched with:
- DEVIATION_MM: The absolute difference between MEASUREMENT_MM and TOLERANCE_MM. If MEASUREMENT_MM is missing, set to empty/null.
- WEIGHT_ERROR: The absolute difference between ACTUAL_WEIGHT and TARGET_WEIGHT divided by TARGET_WEIGHT (as a decimal). If ACTUAL_WEIGHT is missing, set to empty/null.
- QUALITY_GRADE: Based on DEVIATION_MM:
  - "A" if DEVIATION_MM <= 0.5
  - "B" if 0.5 < DEVIATION_MM <= 1.0
  - "C" if DEVIATION_MM > 1.0
  - "N/A" if DEVIATION_MM is missing

Save the final results in `/root/quality_report.xlsx`
