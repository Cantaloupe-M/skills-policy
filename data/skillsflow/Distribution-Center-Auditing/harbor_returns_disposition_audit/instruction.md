You are supporting a returns-processing audit for disposition accuracy.

You are given three files:
- `/root/Return_Plan.xlsx`
- `/root/Disposition_Event_Log.xlsx`
- `/root/Disposition_Alias.xlsx`

## Deliverables
Create both files below:
1. `/root/Returns_Disposition_Audit.xlsx`
2. `/root/Returns_Disposition_Brief.docx`

## Excel Requirements
Build `/root/Returns_Disposition_Audit.xlsx` with exactly these worksheets:
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `RawData`
- Copy the plan table from `Return_Plan.xlsx` exactly.

### 2) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 8 columns exactly as:
  1. Return ID
  2. Line ID
  3. Planned Disposition
  4. Reason Code
  5. Requested Qty
  6. Warehouse
  7. Carrier
  8. Lane
- Add four new columns (columns 9-12) with exactly these headers:
  9. Missing Final Event
  10. Disposition Mismatch
  11. Total Errors
  12. Error Summary

To derive event status, use `Disposition_Event_Log.xlsx` and keep only the latest row with `Event Status = COMPLETED` for each `(Return ID, Line ID)`. Ignore rows with other statuses.

To normalize dispositions, use `Disposition_Alias.xlsx`. If the `Final Disposition` from the kept event matches an alias (case-insensitive), map it to the standard disposition before comparison. If no alias matches, compare the raw text directly (case-insensitive).

Use these rules:
- `Missing Final Event` = 1 if no kept `COMPLETED` event exists for that `(Return ID, Line ID)`, else 0.
- `Disposition Mismatch` = 1 if a kept event exists and the normalized `Final Disposition` does not match `Planned Disposition` (case-insensitive), else 0.
- `Total Errors` = `Missing Final Event + Disposition Mismatch`.
- `Error Summary` must be exactly one of:
  - `None`
  - `Missing Final Event`
  - `Disposition Mismatch`
  - `Missing Final Event, Disposition Mismatch`

For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 3) `Summary`
Create a drill-down summary table with exactly these headers:
1. Warehouse
2. Carrier
3. Missing Final Events
4. Disposition Mismatches
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(Warehouse, Carrier)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `Warehouse` ascending, then `Carrier` ascending.
- Append a final row with:
  - `Warehouse` = `Grand Total`
  - `Carrier` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Returns_Disposition_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`Missing Final Event` and `Disposition Mismatch`).
- The computed totals for Missing Final Events, Disposition Mismatches, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority return IDs with frequent exceptions.

## Important Constraints
- Keep output filenames and worksheet names exactly as specified.
