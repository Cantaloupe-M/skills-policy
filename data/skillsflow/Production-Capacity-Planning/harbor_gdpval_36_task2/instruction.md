You are a CNC operations supervisor building a catch-up plan for milling machine capacity.

Use `/root/mill_demand_sheet.xlsx` (sheet `Mill`) and generate two deliverables:

1. `/root/mill_catch_up_plan.xlsx`
2. `/root/mill_catch_up_summary.txt`

## Data to use

- Periods: 1 through 52 inclusive.
- Scheduled demand: the row labeled `CNC Mill Demand (Hrs)`.
- Initial condition at Period 1: `Start of Period Past Due + Scheduled Demand = 538.08`.
- Production rate: 25 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.

## Required policy (deterministic)

For each period in order:

1. `Start of Period Past Due (Std Hrs) = max(0, prior period End of Period Backlog/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior period End of Period Backlog/Buffer` (Period 1 starts from the initial condition).
3. Choose `Days Worked`:
   - If reported `Start of Period Past Due > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (25 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Period Past Due <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 125`, else choose 5.
4. `Weekly Capacity (Std Hrs) = 25 * Days Worked`
5. `End of Period Backlog/Buffer (Std Hrs) = Calc Start + Scheduled Demand - Weekly Capacity`
6. `Overtime Hours = 10 * max(0, Days Worked - 4)`

## Workbook format requirements

Create a single worksheet named `Plan` with exactly these headers in row 1:

1. `Period`
2. `Days Worked`
3. `Scheduled Demand (Std Hrs)`
4. `Weekly Capacity (Std Hrs)`
5. `Start of Period Past Due (Std Hrs)`
6. `End of Period Backlog/Buffer (Std Hrs)`
7. `Overtime Hours`

Add one row per period for Periods 1..52 (52 rows total), in ascending period order with no gaps/duplicates.

## Summary file format

Create `/root/mill_catch_up_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <period-number-or-N/A>`
2. `First_Week_4_Days: <period-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down period numbers (or `N/A` if not reached).
