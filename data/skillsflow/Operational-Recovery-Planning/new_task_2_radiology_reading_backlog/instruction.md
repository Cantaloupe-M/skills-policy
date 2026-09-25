# Radiology Reading Backlog Stabilization

You are a radiology operations manager scheduling reading capacity to stabilize interpretation backlog.

Use `/root/radiology_reading_reference.xlsx` (sheet `Reads`) and generate two deliverables:

1. `/root/radiology_recovery_plan.xlsx`
2. `/root/radiology_recovery_summary.txt`

## Data to use

- Weeks: 6 through 54 inclusive.
- Scheduled demand: the row labeled `Reading Load Forecast Total` on sheet `Reads`.
- Initial condition at Week 6: `Start of Week Queue + Scheduled Demand = 468.55`.
- Production rate: 26 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.


## Required policy (deterministic)

For each week in order:

1. `Start of Week Queue = max(0, prior week End of Week Queue/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior week End of Week Queue/Buffer` (Week 6 starts from the initial condition).
3. Choose the day count for the week:
   - If reported `Start of Week Queue > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (26 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Week Queue <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 104.00`, else choose 5.
4. `Weekly Capacity = 26 * Days Worked`
5. `End of Week Queue/Buffer = Calc Start + Scheduled Demand - Weekly Capacity`
6. `Overtime Hours = 6 * max(0, Days Worked - 4)`

## Workbook format requirements

The output workbook must contain a worksheet named `Plan`.
Use exactly these headers in row 1:

1. `Week`
2. `Radiologist Days`
3. `Forecast Reading Load (Scan Hrs)`
4. `Weekly Reading Capacity (Scan Hrs)`
5. `Start-of-Week Reading Backlog (Scan Hrs)`
6. `End-of-Week Reading Backlog/Buffer (Scan Hrs)`
7. `Surge Premium Hours`

Add one row per week for Weeks 6..54 (49 rows total), in ascending week order with no gaps or duplicates.

## Summary file format

Create `/root/radiology_recovery_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <week-number-or-N/A>`
2. `First_Week_4_Days: <week-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down week numbers (or `N/A` if not reached).
- The summary text must include the exact phrase(s): `Project PulseLift`, `Milestone`.
