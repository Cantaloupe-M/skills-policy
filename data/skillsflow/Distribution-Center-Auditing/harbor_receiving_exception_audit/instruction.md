You are supporting a distribution-center receiving review for inbound grocery loads.

You are given one source workbook:
- `/root/Receiving_Log.xlsx`

## Deliverables
Create both files below:
1. `/root/Receiving_Exception_Audit.xlsx`
2. `/root/Receiving_Exception_Brief.docx`

## Excel Requirements
Build `/root/Receiving_Exception_Audit.xlsx` with exactly these worksheets:
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `RawData`
- Copy the source table from `Receiving_Log.xlsx` exactly.

### 2) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 8 columns exactly as:
  1. Receipt ID
  2. Item Code
  3. Expected Qty
  4. Received Qty
  5. Storage Class
  6. Temp Status
  7. Supplier
  8. Dock
- Add four new columns (columns 9-12) with exactly these headers:
  9. Qty Variance
  10. Cold Chain Error
  11. Total Errors
  12. Error Summary

Use these rules:
- `Qty Variance` = 1 if `Received Qty` != `Expected Qty`, else 0.
- `Cold Chain Error` = 1 only when `Storage Class` is `CHILLED` or `FROZEN` (case-insensitive) and `Temp Status` is not `OK` (case-insensitive). Otherwise 0.
- `Total Errors` = `Qty Variance + Cold Chain Error`.
- `Error Summary` must be exactly one of:
  - `None`
  - `Qty Variance`
  - `Cold Chain Error`
  - `Qty Variance, Cold Chain Error`

For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 3) `Summary`
Create a drill-down summary table with exactly these headers:
1. Item Code
2. Supplier
3. Qty Variance Errors
4. Cold Chain Errors
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(Item Code, Supplier)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `Item Code` ascending, then `Supplier` ascending.
- Append a final row with:
  - `Item Code` = `Grand Total`
  - `Supplier` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Receiving_Exception_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`Qty Variance` and `Cold Chain Error`).
- The computed totals for Qty Variance errors, Cold Chain errors, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority item codes with frequent exceptions.

## Important Constraints
- Keep output filenames and worksheet names exactly as specified.
