You are a Senior Staff Accountant at Aurisic.

Build an Excel workbook at:

- `/root/Aurisic_Amortization_4-25.xlsx`

Use these normalized input files:

- `/root/prepaid_expenses_schedule_input.csv`
- `/root/prepaid_insurance_schedule_input.csv`
- `/root/gl_balances.json`

For audit context only, the original source documents are also present:

- `/root/COA.xlsx`
- `/root/Aurisic_Prepaid_Expenses_Jan25.pdf`
- `/root/Aurisic_Prepaid_Expenses_Feb25.pdf`
- `/root/Aurisic_Prepaid_Expenses_Mar25.pdf`
- `/root/Aurisic_Prepaid_Expenses_Apr25.pdf`
- `/root/Aurisic_Prepaid_Insurance.pdf`

Create exactly three sheets in this order:

1. `Prepaid Summary`
2. `PPD Exp #1250`
3. `PPD Ins #1251`

Populate the two detailed sheets using one row per CSV line item, starting at row 6, with this column layout:

- A: Vendor
- B: Beginning Balance
- C: Jan Adds
- D: Jan Amortization
- E: Jan Ending Balance
- F: Feb Adds
- G: Feb Amortization
- H: Feb Ending Balance
- I: Mar Adds
- J: Mar Amortization
- K: Mar Ending Balance
- L: Apr Adds
- M: Apr Amortization
- N: Apr Ending Balance
- O: Amortization Months
- P: Comments
- Q: Account Number

For each detailed sheet, include these control rows immediately below the line items:

- `Month Totals`
- `Ending Balance`
- `Variance`
- `GL Balance`

Required control-row formulas:

- `Month Totals` row:
  - Columns B:N use `SUM(...)` over all line-item rows.
  - Column O formula: `C + F + I + L` (same row).
- `Ending Balance` row:
  - E = B + C - D
  - H = E + F - G
  - K = H + I - J
  - N = K + L - M
  - O = D + G + J + M
- `Variance` row:
  - Column O formula: `O(GL Balance row) - N(GL Balance row)`
- `GL Balance` row:
  - Columns E/H/K/N must match `/root/gl_balances.json` for the corresponding account.
  - Column O formula: `O(Month Totals row) - O(Ending Balance row)`

Summary sheet requirements:

- Include company name (`Aurisic`) and period through April 30, 2025.
- Include sections for both accounts (`1250` and `1251`).
- Use formulas in these cells:
  - `B7` links to column O of `PPD Exp #1250` Month Totals row
  - `B8` links to column O of `PPD Exp #1250` Ending Balance row
  - `B9` links to column O of `PPD Exp #1250` GL Balance row
  - `B12` links to column O of `PPD Ins #1251` Month Totals row
  - `B13` links to column O of `PPD Ins #1251` Ending Balance row
  - `B14` links to column O of `PPD Ins #1251` GL Balance row
  - `B16` formula: `B9 + B14`

Important:

- Keep currency values numeric (not text).
- Do not change source files.
- Final deliverable must be a single `.xlsx` workbook at the required path.
