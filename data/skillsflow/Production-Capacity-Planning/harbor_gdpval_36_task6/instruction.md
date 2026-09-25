You are a textile manufacturing supervisor building a catch-up plan for dyeing process capacity.

Use `/root/dye_demand_sheet.xlsx` (sheets `Dye` and `Adjust`) and generate two deliverables:

1. `/root/dye_catch_up_plan.xlsx`
2. `/root/dye_catch_up_summary.txt`

## Data to use

- Weeks: 3 through 51 inclusive.
- The `Dye` sheet contains base demand: row labeled `Dye Demand (Std Hrs)`.
- The `Adjust` sheet contains weekly demand adjustments: row labeled `Demand Adjustment (Std Hrs)`.
- **Effective demand = Dye Demand + Demand Adjustment** for each week.
- Initial condition at Week 3: `Start of Week Past Due + Scheduled Demand = 598.24`.
- Production rate: 18 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.

## Required policy (deterministic)

For each week in order:

1. `Start of Week Past Due (Std Hrs) = max(0, prior week End of Week Backlog/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior week End of Week Backlog/Buffer` (Week 3 starts from the initial condition).
3. Choose `Days Worked`:
   - If reported `Start of Week Past Due > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (18 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Week Past Due <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 72`, else choose 5.
4. `Weekly Capacity (Std Hrs) = 18 * Days Worked`
5. `End of Week Backlog/Buffer (Std Hrs) = Calc Start + Scheduled Demand - Weekly Capacity`
6. `Overtime Hours = 10 * max(0, Days Worked - 4)`

## Workbook format requirements

Create a single worksheet named `Plan` with exactly these headers in row 1:

1. `Week`
2. `Days Worked`
3. `Scheduled Demand (Std Hrs)`
4. `Weekly Capacity (Std Hrs)`
5. `Start of Week Past Due (Std Hrs)`
6. `End of Week Backlog/Buffer (Std Hrs)`
7. `Overtime Hours`

Add one row per week for Weeks 3..51 (49 rows total), in ascending week order with no gaps/duplicates.

## Summary file format

Create `/root/dye_catch_up_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <week-number-or-N/A>`
2. `First_Week_4_Days: <week-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down week numbers (or `N/A` if not reached).
