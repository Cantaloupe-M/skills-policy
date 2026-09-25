You are assisting infrastructure operations in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/hardware_registry_q1.pdf`.
The current operational dataset is stored in Excel format at `/root/hardware_registry_q2.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/hardware_diff_report.json` in the following JSON format:

```json
{
  "decommissioned_servers": [
    "SVR0007",
    "SVR0055"
  ],
  "updated_servers": [
    {
      "id": "SVR0014",
      "field": "CPUCores",
      "old_value": 16,
      "new_value": 32
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^SVR\d{4}$`.
- Numeric fields (`CPUCores`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `decommissioned_servers` and `updated_servers` by ID for deterministic output.
