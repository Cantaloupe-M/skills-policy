You are assisting a cloud cost governance team in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/cloud_service_portfolio_archive.pdf`.
The current operational dataset is stored in Excel format at `/root/cloud_service_portfolio_current.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/cloud_service_portfolio_diff.json` in the following JSON format:

```json
{
  "retired_service_ids": [
    "CSV0006",
    "CSV0009"
  ],
  "changed_services": [
    {
      "id": "CSV0001",
      "field": "Spend2024K",
      "old_value": 10128,
      "new_value": 10360
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^CSV\d{4}$`.
- Numeric fields (`Spend2019K`, `Spend2024K`, `FiveYearCAGR`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `retired_service_ids` and `changed_services` by ID for deterministic output.
