You are assisting an academic affairs office in reconciling an archived PDF snapshot against the latest workbook.

The archived snapshot is stored in PDF format at `/root/course_catalog_2024.pdf`.
The current operational dataset is stored in Excel format at `/root/course_catalog_2025.xlsx`.

Your task is to:

1. Extract the full table from the archived PDF.
2. Compare it against the current Excel file using `ID` as the primary key.
3. Detect:
   - which IDs were removed from the current dataset,
   - which records were modified (include `id`, `field`, `old_value`, and `new_value`).

Write the final result to `/root/course_diff_report.json` in the following JSON format:

```json
{
  "removed_courses": [
    "CRS0004",
    "CRS0049"
  ],
  "revised_courses": [
    {
      "id": "CRS0035",
      "field": "Instructor",
      "old_value": "Dr. Chen",
      "new_value": "Prof. Elena Torres"
    }
  ]
}
```

Notes:
- The PDF contains the older baseline snapshot.
- The Excel file contains the newer current snapshot.
- ID values must match pattern `^CRS\d{4}$`.
- Numeric fields (`Credits`) must be output as numbers.
- Text fields must be output as strings.
- If a record has multiple changed fields, emit one object per field.
- Sort both `removed_courses` and `revised_courses` by ID for deterministic output.
