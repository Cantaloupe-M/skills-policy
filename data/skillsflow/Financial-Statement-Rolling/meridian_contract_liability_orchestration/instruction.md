You are completing the December 2025 contract liability package for Meridian Mobility Network. Update the existing workbook template from the sparse export payload, alias routing file, manual bridge, and GL checkpoints.

Build the workbook at:

- `/root/Meridian_Contract_Liability_12-25.xlsx`

Use these source files:

- `/root/liability_template.xlsx`
- `/root/contract_liability_dump.json`
- `/root/bucket_aliases.csv`
- `/root/manual_bridge.csv`
- `/root/gl_balances.json`

Create exactly three sheets in this order:

1. `Contract Liability Summary`
2. `Subscriptions #2350`
3. `Services #2355`

Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

- A: Customer
- B: Beginning Balance
- C: Sep Billings
- D: Sep Revenue
- E: Sep Ending Balance
- F: Oct Billings
- G: Oct Revenue
- H: Oct Ending Balance
- I: Nov Billings
- J: Nov Revenue
- K: Nov Ending Balance
- L: Dec Billings
- M: Dec Revenue
- N: Dec Ending Balance
- O: Contract Months
- P: Notes
- Q: Liability Account

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

- Include company name (`Meridian Mobility Network`) and the period ending shown in the source package.
- Include sections for both accounts.
- Use formulas in these cells:
  - `B7` links to column `O` of `Subscriptions #2350` Period Totals row
  - `B8` links to column `O` of `Subscriptions #2350` Ending Balance row
  - `B9` links to column `O` of `Subscriptions #2350` GL Balance row
  - `B12` links to column `O` of `Services #2355` Period Totals row
  - `B13` links to column `O` of `Services #2355` Ending Balance row
  - `B14` links to column `O` of `Services #2355` GL Balance row
  - `B16` formula: `B9 + B14`

Before populating the detailed sheets:

- Start from `/root/liability_template.xlsx` and save the finished workbook to the required output path.
- Route each export section by `/root/bucket_aliases.csv`.
- Keep only records where `active_flag` is true and `record_type` is `detail`.
- If multiple records share the same `contract_key` within a bucket, keep the highest `revision_no`.
- Missing months in `month_roll` represent zero billings and zero revenue for that month.
- Apply `/root/manual_bridge.csv` after normalization:
  - `action=override` replaces any nonblank field on the matching row.
  - `action=insert` creates a new row in the matching bucket.
- Recompute each row's ending balances from beginning balance plus billings minus revenue after all bridge overrides are applied.
- Clear any old template content from row 6 downward before writing the refreshed schedule.
- Sort each detailed sheet by customer name, then by `contract_key`.
Important:

- Keep amount cells numeric, not text.
- Do not modify the source files.
- Final deliverable must be a single `.xlsx` workbook at the required path.
