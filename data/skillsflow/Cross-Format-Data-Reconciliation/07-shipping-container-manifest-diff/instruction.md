You are assisting a port operations team in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/container_manifest_old.pdf`.
The current operational dataset is stored in Excel format at `/root/container_manifest_current.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/container_diff_report.json` in the following JSON format:

```json
{
  "missing_containers": [
    "CNT0009",
    "CNT0063"
  ],
  "changed_containers": [
    {
      "id": "CNT0018",
      "field": "WeightTons",
      "old_value": 45.8,
      "new_value": 44.2
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^CNT\d{4}$`.
- Numeric fields (`WeightTons`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `missing_containers` and `changed_containers` by ID for deterministic output.
