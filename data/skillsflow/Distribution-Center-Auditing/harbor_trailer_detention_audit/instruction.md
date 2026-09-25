You are supporting a yard-management review for trailer detention compliance.

You are given one source workbook:
- `/root/Trailer_Detention_Log.xlsx`

## Deliverables
Create both files below:
1. `/root/Trailer_Detention_Audit.xlsx`
2. `/root/Trailer_Detention_Brief.docx`

## Excel Requirements
Build `/root/Trailer_Detention_Audit.xlsx` with exactly these worksheets:
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `RawData`
- Copy the source table from `Trailer_Detention_Log.xlsx` exactly.

### 2) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 8 columns exactly as:
  1. Load ID
  2. Carrier
  3. Allowed Hold Hours
  4. Actual Hold Hours
  5. Seal Required
  6. Seal Status
  7. Yard
  8. Dispatcher
- Add four new columns (columns 9-12) with exactly these headers:
  9. Detention Overrun
  10. Seal Error
  11. Total Errors
  12. Error Summary

Use these rules:
- `Detention Overrun` = 1 if `Actual Hold Hours` is greater than `Allowed Hold Hours`, else 0.
- `Seal Error` = 1 only when `Seal Required` is `YES` (case-insensitive) and `Seal Status` is not `VERIFIED` (case-insensitive). Otherwise 0.
- `Total Errors` = `Detention Overrun + Seal Error`.
- `Error Summary` must be exactly one of:
  - `None`
  - `Detention Overrun`
  - `Seal Error`
  - `Detention Overrun, Seal Error`

For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 3) `Summary`
Create a drill-down summary table with exactly these headers:
1. Carrier
2. Yard
3. Detention Overrun Errors
4. Seal Errors
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(Carrier, Yard)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `Carrier` ascending, then `Yard` ascending.
- Append a final row with:
  - `Carrier` = `Grand Total`
  - `Yard` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Trailer_Detention_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`Detention Overrun` and `Seal Error`).
- The computed totals for Detention Overrun errors, Seal errors, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority carriers with frequent exceptions.

## Important Constraints
- Keep output filenames and worksheet names exactly as specified.
