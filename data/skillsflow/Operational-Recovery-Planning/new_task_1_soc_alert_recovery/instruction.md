# SOC Alert Queue Catch-Up Plan

You are a security operations lead planning analyst capacity to control the weekly alert triage queue.

Use `/root/alert_load_reference.xlsx` (sheet `Alerts`) and generate two deliverables:

1. `/root/soc_queue_plan.xlsx`
2. `/root/soc_queue_summary.txt`

## Data to use

- Weeks: 1 through 40 inclusive.
- Scheduled demand: the row labeled `Security Alert Load Total` on sheet `Alerts`.
- Initial condition at Week 1: `Start of Week Queue + Scheduled Demand = 512.40`.
- Production rate: 28 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.


## Required policy (deterministic)

For each week in order:

1. `Start of Week Queue = max(0, prior week End of Week Queue/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior week End of Week Queue/Buffer` (Week 1 starts from the initial condition).
3. Choose the day count for the week:
   - If reported `Start of Week Queue > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (28 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Week Queue <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 112.00`, else choose 5.
4. `Weekly Capacity = 28 * Days Worked`
5. `End of Week Queue/Buffer = Calc Start + Scheduled Demand - Weekly Capacity`
6. `Overtime Hours = 8 * max(0, Days Worked - 4)`

## Workbook format requirements

The output workbook must contain a worksheet named `Plan`.
Use exactly these headers in row 1:

1. `Week`
2. `On-Call Days`
3. `Forecast Alert Load (Analyst Hrs)`
4. `Weekly Triage Capacity (Analyst Hrs)`
5. `Start-of-Week Alert Queue (Analyst Hrs)`
6. `End-of-Week Alert Queue/Buffer (Analyst Hrs)`
7. `Burnout Overtime Hours`

Add one row per week for Weeks 1..40 (40 rows total), in ascending week order with no gaps or duplicates.

## Summary file format

Create `/root/soc_queue_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <week-number-or-N/A>`
2. `First_Week_4_Days: <week-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down week numbers (or `N/A` if not reached).
