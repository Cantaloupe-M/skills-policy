You are assisting a hospital pharmacy team in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/medications_archive.pdf`.
The current operational dataset is stored in Excel format at `/root/medications_live.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/medication_diff_report.json` in the following JSON format:

```json
{
  "deleted_medications": [
    "MED00012",
    "MED00044"
  ],
  "modified_medications": [
    {
      "id": "MED00017",
      "field": "StockUnits",
      "old_value": 213,
      "new_value": 195
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^MED\d{5}$`.
- Numeric fields (`StockUnits`, `ReorderLevel`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `deleted_medications` and `modified_medications` by ID for deterministic output.
