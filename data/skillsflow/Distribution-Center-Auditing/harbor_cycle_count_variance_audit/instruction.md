You are supporting a cycle-count variance audit for inventory accuracy.

You are given three files:
- `/root/Cycle_Plan.xlsx`
- `/root/Count_Event_Log.xlsx`
- `/root/Cycle_Template.xlsx`

## Deliverables
Create both files below:
1. `/root/Cycle_Count_Variance_Audit.xlsx`
2. `/root/Cycle_Count_Variance_Brief.docx`

## Excel Requirements
Build `/root/Cycle_Count_Variance_Audit.xlsx` with exactly these worksheets:
- `Overview`
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `Overview`
- Copy the `Overview` sheet from `Cycle_Template.xlsx` exactly and preserve it unchanged.

### 2) `RawData`
- Copy the plan table from `Cycle_Plan.xlsx` exactly.

### 3) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 7 columns exactly as:
  1. Facility
  2. Session ID
  3. Bin ID
  4. Product ID
  5. Expected Qty
  6. Allowed Variance
  7. Approval Needed
- Add four new columns (columns 8-11) with exactly these headers:
  8. Missing Final Count
  9. Approval Gap
  10. Total Errors
  11. Error Summary

To derive final count, use `Count_Event_Log.xlsx` and keep only the latest row with `Event Type = FINAL` for each `(Facility, Session ID, Bin ID)`. Ignore rows with blank keys or blank `Count Qty`.

Use these rules:
- `Missing Final Count` = 1 if no kept `FINAL` event exists for that key, else 0.
- `Approval Gap` = 1 if all three conditions hold:
  1. A kept final event exists.
  2. `Approval Needed` = `YES` (case-insensitive).
  3. The absolute difference between `Expected Qty` and `Count Qty` is strictly greater than `Allowed Variance`.
  Otherwise 0.
- `Total Errors` = `Missing Final Count + Approval Gap`.
- `Error Summary` must be exactly one of:
  - `None`
  - `Missing Final Count`
  - `Approval Gap`
  - `Missing Final Count, Approval Gap`

For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 4) `Summary`
Create a drill-down summary table with exactly these headers:
1. Facility
2. Session ID
3. Missing Final Counts
4. Approval Gaps
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(Facility, Session ID)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `Facility` ascending, then `Session ID` ascending.
- Append a final row with:
  - `Facility` = `Grand Total`
  - `Session ID` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Cycle_Count_Variance_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`Missing Final Count` and `Approval Gap`).
- The computed totals for Missing Final Counts, Approval Gaps, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority facility-session combinations with frequent exceptions.

## Important Constraints
- Preserve the `Overview` sheet from the template unchanged.
- Keep output filenames and worksheet names exactly as specified.
