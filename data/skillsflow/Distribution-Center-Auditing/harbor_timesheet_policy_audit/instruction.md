You are supporting an operations-compliance review for weekly consultant timesheets.

You are given one source workbook:
- `/root/Timesheet_Submissions.xlsx`

The workbook includes an `Entries` sheet with line-level submissions and a `BreakRules` sheet with role-based thresholds.

## Deliverables
Create both files below:
1. `/root/Timesheet_Compliance_Audit.xlsx`
2. `/root/Timesheet_Compliance_Brief.docx`

## Excel Requirements
Build `/root/Timesheet_Compliance_Audit.xlsx` with exactly these worksheets:
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `RawData`
- Copy the `Entries` table exactly.

### 2) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 8 columns exactly as:
  1. Week Ending
  2. Employee ID
  3. Role
  4. Hours Worked
  5. Break Minutes
  6. Approval Code
  7. Project Code
  8. Manager
- Add four new columns (columns 9-12) with exactly these headers:
  9. Break Deficit
  10. Approval Missing
  11. Total Errors
  12. Error Summary

Use these rules:
- `Break Deficit` = 1 if `Break Minutes` is less than the `Min Break Minutes` for that row's `Role` from `BreakRules`, else 0.
- `Approval Missing` = 1 if `Hours Worked` is greater than the `Overtime Threshold` for that row's `Role` from `BreakRules` and `Approval Code` is blank, else 0.
- `Total Errors` = `Break Deficit + Approval Missing`.
- `Error Summary` must be exactly one of:
  - `None`
  - `Break Deficit`
  - `Approval Missing`
  - `Break Deficit, Approval Missing`

For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 3) `Summary`
Create a drill-down summary table with exactly these headers:
1. Employee ID
2. Week Ending
3. Break Deficits
4. Approval Gaps
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(Employee ID, Week Ending)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `Employee ID` ascending, then `Week Ending` ascending.
- Append a final row with:
  - `Employee ID` = `Grand Total`
  - `Week Ending` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Timesheet_Compliance_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`Break Deficit` and `Approval Missing`).
- The computed totals for Break Deficits, Approval Gaps, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority employee IDs with frequent exceptions.

## Important Constraints
- Use the thresholds from `BreakRules` rather than hardcoding them by role name.
- Keep output filenames and worksheet names exactly as specified.
