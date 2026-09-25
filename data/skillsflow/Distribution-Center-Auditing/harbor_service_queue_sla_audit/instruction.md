You are supporting a service-desk SLA review for queue health.

You are given one source workbook:
- `/root/Ticket_Queue.xlsx`

The workbook includes a `Tickets` sheet with row-level tickets and an `SLA_Rules` sheet with priority thresholds.

## Deliverables
Create both files below:
1. `/root/Service_Queue_SLA_Audit.xlsx`
2. `/root/Service_Queue_SLA_Brief.docx`

## Excel Requirements
Build `/root/Service_Queue_SLA_Audit.xlsx` with exactly these worksheets:
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `RawData`
- Copy the `Tickets` table exactly.

### 2) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 8 columns exactly as:
  1. Ticket ID
  2. Queue
  3. Priority Tier
  4. Open Age Hours
  5. Owner
  6. Escalation Code
  7. Region
  8. Analyst
- Add four new columns (columns 9-12) with exactly these headers:
  9. SLA Breach
  10. Missing Escalation
  11. Total Errors
  12. Error Summary

Use these rules:
- `SLA Breach` = 1 if `Open Age Hours` is greater than the `Max Open Hours` for that row's `Priority Tier` from `SLA_Rules`, else 0.
- `Missing Escalation` = 1 if `Escalation Required` is `Y` for that row's `Priority Tier` from `SLA_Rules` and `Escalation Code` is blank, else 0.
- `Total Errors` = `SLA Breach + Missing Escalation`.
- `Error Summary` must be exactly one of:
  - `None`
  - `SLA Breach`
  - `Missing Escalation`
  - `SLA Breach, Missing Escalation`

For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 3) `Summary`
Create a drill-down summary table with exactly these headers:
1. Queue
2. Region
3. SLA Breaches
4. Missing Escalations
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(Queue, Region)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `Queue` ascending, then `Region` ascending.
- Append a final row with:
  - `Queue` = `Grand Total`
  - `Region` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Service_Queue_SLA_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`SLA Breach` and `Missing Escalation`).
- The computed totals for SLA Breaches, Missing Escalations, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority queues with frequent exceptions.

## Important Constraints
- Use the thresholds from `SLA_Rules` rather than hardcoding them by priority tier.
- Keep output filenames and worksheet names exactly as specified.
