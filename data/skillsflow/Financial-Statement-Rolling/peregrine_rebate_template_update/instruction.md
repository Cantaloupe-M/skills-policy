You are refreshing the October 2025 rebate reserve package for Peregrine Devices. Update the existing workbook template using the base schedules, patch file, and GL checkpoints.

    Build the workbook at:

    - `/root/Peregrine_Rebate_Rollforward_10-25.xlsx`

    Use these source files:

    - `/root/rebate_template.xlsx`
- `/root/channel_rebate_base.csv`
- `/root/mdf_base.csv`
- `/root/schedule_patch.csv`
- `/root/gl_balances.json`

    Create exactly three sheets in this order:

    1. `Rebate Summary`
    2. `Channel Rebates #6120`
    3. `MDF Accrual #6125`

    Populate the two detailed sheets using one row per final schedule line item, starting at row 6, with this column layout:

    - A: Partner
- B: Beginning Balance
- C: Jul Accruals
- D: Jul Utilization
- E: Jul Ending Balance
- F: Aug Accruals
- G: Aug Utilization
- H: Aug Ending Balance
- I: Sep Accruals
- J: Sep Utilization
- K: Sep Ending Balance
- L: Oct Accruals
- M: Oct Utilization
- N: Oct Ending Balance
- O: Reserve Months
- P: Notes
- Q: Expense Account

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

    - Include company name (`Peregrine Devices`) and the period ending shown in the source package.
    - Include sections for both accounts.
    - Use formulas in these cells:
      - `B7` links to column `O` of `Channel Rebates #6120` Period Totals row
- `B8` links to column `O` of `Channel Rebates #6120` Ending Balance row
- `B9` links to column `O` of `Channel Rebates #6120` GL Balance row
- `B12` links to column `O` of `MDF Accrual #6125` Period Totals row
- `B13` links to column `O` of `MDF Accrual #6125` Ending Balance row
- `B14` links to column `O` of `MDF Accrual #6125` GL Balance row
- `B16` formula: `B9 + B14`

    Before populating the detailed sheets:

- Start from `/root/rebate_template.xlsx` and save the finished workbook to the required output path.
- Keep only base rows where `status` is `open`.
- Apply `/root/schedule_patch.csv` by `row_key`:
  - `action=override` replaces any nonblank field on the matching base row.
  - `action=insert` creates a new row for the `target_sheet`.
- Sort each detailed sheet by partner name, then by `row_key`.
- Clear any prefilled detail content from row 6 downward before writing the current schedule so no stale template rows remain.

    Important:

    - Keep amount cells numeric, not text.
    - Do not modify the source files.
    - Final deliverable must be a single `.xlsx` workbook at the required path.
