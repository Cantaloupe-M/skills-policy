You are assisting a regional hospital planning office in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/hospital_capacity_archive.pdf`.
The current operational dataset is stored in Excel format at `/root/hospital_capacity_current.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/hospital_capacity_diff_report.json` in the following JSON format:

```json
{
  "closed_departments": [
    "HCP0006",
    "HCP0009"
  ],
  "updated_departments": [
    {
      "id": "HCP0001",
      "field": "Capacity2024",
      "old_value": 9284,
      "new_value": 9420
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^HCP\d{4}$`.
- Numeric fields (`Capacity2019`, `Capacity2024`, `FiveYearCAGR`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `closed_departments` and `updated_departments` by ID for deterministic output.
