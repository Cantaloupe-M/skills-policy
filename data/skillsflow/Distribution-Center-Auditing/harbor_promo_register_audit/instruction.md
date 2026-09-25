You are helping a retail pricing team verify promotional register performance.

You are given one source workbook:
- `/root/Promo_Price_Check_Source.xlsx`

## Deliverables
Create both files below:
1. `/root/Promo_Register_Audit.xlsx`
2. `/root/Promo_Register_Brief.docx`

## Excel Requirements
Build `/root/Promo_Register_Audit.xlsx` with exactly these worksheets:
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `RawData`
- Copy the source table from `Promo_Price_Check_Source.xlsx` exactly.

### 2) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 8 columns exactly as:
  1. Promo ID
  2. SKU
  3. Promo Price
  4. Register Price
  5. Promo Start Date
  6. Sale Date
  7. Promo End Date
  8. Store ID
- Add four new columns (columns 9-12) with exactly these headers:
  9. Price Error
  10. Window Error
  11. Total Errors
  12. Error Summary

Use these rules:
- `Price Error` = 1 if `Register Price` != `Promo Price`, else 0.
- `Window Error` = 1 if `Sale Date` is earlier than `Promo Start Date` or later than `Promo End Date`, else 0.
- `Total Errors` = `Price Error + Window Error`.
- `Error Summary` must be exactly one of:
  - `None`
  - `Price Error`
  - `Window Error`
  - `Price Error, Window Error`

Treat the date columns as calendar dates. For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 3) `Summary`
Create a drill-down summary table with exactly these headers:
1. SKU
2. Store ID
3. Price Errors
4. Window Errors
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(SKU, Store ID)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `SKU` ascending, then `Store ID` ascending.
- Append a final row with:
  - `SKU` = `Grand Total`
  - `Store ID` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Promo_Register_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`Price Error` and `Window Error`).
- The computed totals for Price Errors, Window Errors, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority SKUs with frequent exceptions.

## Important Constraints
- Keep output filenames and worksheet names exactly as specified.
