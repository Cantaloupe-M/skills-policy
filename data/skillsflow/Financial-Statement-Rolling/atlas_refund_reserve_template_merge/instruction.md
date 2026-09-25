You are refreshing the November 2025 refund reserve package for Atlas Cloud Commerce. Update the existing workbook template from the versioned refund snapshots, the adjustment file, and the GL checkpoints.

Build the workbook at:

- `/root/Atlas_Refund_Reserve_11-25.xlsx`

Use these source files:

- `/root/refund_template.xlsx`
- `/root/refund_snapshot.json`
- `/root/refund_adjustments.csv`
- `/root/gl_balances.json`

Create exactly three sheets in this order:

1. `Refund Summary`
2. `Enterprise Refunds #2215`
3. `SMB Refunds #2218`

Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

- A: Customer
- B: Beginning Balance
- C: Aug Refund Accruals
- D: Aug Credits Issued
- E: Aug Ending Balance
- F: Sep Refund Accruals
- G: Sep Credits Issued
- H: Sep Ending Balance
- I: Oct Refund Accruals
- J: Oct Credits Issued
- K: Oct Ending Balance
- L: Nov Refund Accruals
- M: Nov Credits Issued
- N: Nov Ending Balance
- O: Reserve Months
- P: Notes
- Q: Reserve Account

For each detailed sheet, place these control rows immediately below the line items:

- `Period Totals`
- `Ending Balance`
- `Variance`
- `GL Balance`

Required control-row formulas:

- `Period Totals` row:
  - Columns `B:N` use `SUM(...)` over all line-item rows.
  - Column `O` formula: `C + F + I + L` (same row).
- `Ending Balance` row:
  - `E` = `B + C - D`
  - `H` = `E + F - G`
  - `K` = `H + I - J`
  - `N` = `K + L - M`
  - `O` = `D + G + J + M`
- `Variance` row:
  - Column `O` formula: `O(GL Balance row) - N(GL Balance row)`
- `GL Balance` row:
  - Columns `E/H/K/N` must match `/root/gl_balances.json` for the corresponding account.
  - Column `O` formula: `O(Period Totals row) - O(Ending Balance row)`

Summary sheet requirements:

- Include company name (`Atlas Cloud Commerce`) and the period ending shown in the source package.
- Include sections for both accounts.
- Use formulas in these cells:
  - `B7` links to column `O` of `Enterprise Refunds #2215` Period Totals row
  - `B8` links to column `O` of `Enterprise Refunds #2215` Ending Balance row
  - `B9` links to column `O` of `Enterprise Refunds #2215` GL Balance row
  - `B12` links to column `O` of `SMB Refunds #2218` Period Totals row
  - `B13` links to column `O` of `SMB Refunds #2218` Ending Balance row
  - `B14` links to column `O` of `SMB Refunds #2218` GL Balance row
  - `B16` formula: `B9 + B14`

Before populating the detailed sheets:

- Start from `/root/refund_template.xlsx` and save the finished workbook to the required output path.
- Keep only snapshot rows where `approved` is true and `row_kind` is `detail`.
- If multiple rows share the same `case_id`, keep the highest `version`.
- Missing months in `flow_months` represent zero activity for that month.
- Apply `/root/refund_adjustments.csv` after normalization:
  - `action=override` replaces any nonblank field on the matching row.
  - `action=insert` creates a new row in the matching refund bucket.
- Clear any old template content from row 6 downward before writing the refreshed schedule.
- Sort each detailed sheet by customer name, then by `case_id`.
Important:

- Keep amount cells numeric, not text.
- Do not modify the source files.
- Final deliverable must be a single `.xlsx` workbook at the required path.
