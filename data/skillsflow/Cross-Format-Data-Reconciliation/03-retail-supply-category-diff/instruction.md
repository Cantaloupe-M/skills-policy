You are assisting a retail supply planning team in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/retail_supply_archive.pdf`.
The current operational dataset is stored in Excel format at `/root/retail_supply_current.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/retail_supply_diff_report.json` in the following JSON format:

```json
{
  "dropped_categories": [
    "RTL0006",
    "RTL0008"
  ],
  "adjusted_categories": [
    {
      "id": "RTL0001",
      "field": "Spend2024K",
      "old_value": 10972,
      "new_value": 11105
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^RTL\d{4}$`.
- Numeric fields (`Spend2019K`, `Spend2024K`, `FiveYearCAGR`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `dropped_categories` and `adjusted_categories` by ID for deterministic output.
