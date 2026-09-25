You are assisting a university budgeting office in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/university_funding_archive.pdf`.
The current operational dataset is stored in Excel format at `/root/university_funding_current.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/university_funding_diff_report.json` in the following JSON format:

```json
{
  "retired_schools": [
    "UNI0006",
    "UNI0008"
  ],
  "revised_schools": [
    {
      "id": "UNI0001",
      "field": "Funding2024K",
      "old_value": 7596,
      "new_value": 7710
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^UNI\d{4}$`.
- Numeric fields (`Funding2019K`, `Funding2024K`, `FiveYearCAGR`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `retired_schools` and `revised_schools` by ID for deterministic output.
