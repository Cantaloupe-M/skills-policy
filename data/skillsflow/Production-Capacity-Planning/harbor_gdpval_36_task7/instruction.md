You are a shipbuilding operations manager building a catch-up plan for block assembly crew capacity.

Use `/root/ship_demand.csv` and generate two deliverables:

1. `/root/ship_block_plan.xlsx`
2. `/root/ship_block_summary.txt`

## Data to use

- Weeks: 5 through 53 inclusive.
- The CSV is organized with **week numbers as column headers** (not as row labels). The first row contains `Week` followed by week numbers (5, 6, 7, ..., 53). The second row contains `Demand` followed by the demand values for each week.
- You must transpose this layout: treat each column header (after `Week`) as a week number, and the corresponding cell in the `Demand` row as that week's demand.
- Initial condition at Week 5: `Start of Week Past Due + Scheduled Demand = 1014.51`.
- Production rate: 28 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.

## Required policy (deterministic)

For each week in order:

1. `Start of Week Past Due (Std Hrs) = max(0, prior week End of Week Backlog/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior week End of Week Backlog/Buffer` (Week 5 starts from the initial condition).
3. Choose `Days Worked`:
   - If reported `Start of Week Past Due > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (28 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Week Past Due <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 112`, else choose 5.
4. `Weekly Capacity (Std Hrs) = 28 * Days Worked`
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

Add one row per week for Weeks 5..53 (49 rows total), in ascending week order with no gaps/duplicates.

## Summary file format

Create `/root/ship_block_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <week-number-or-N/A>`
2. `First_Week_4_Days: <week-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down week numbers (or `N/A` if not reached).
