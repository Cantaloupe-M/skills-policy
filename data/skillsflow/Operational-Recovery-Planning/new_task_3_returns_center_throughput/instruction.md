# Returns Center Throughput Ramp-Down

You are an e-commerce returns center manager balancing intake workload and processing capacity.

Use `/root/returns_intake_reference.xlsx` (sheet `Returns`) and generate two deliverables:

1. `/root/returns_throughput_plan.xlsx`
2. `/root/returns_throughput_summary.txt`

## Data to use

- Weeks: 3 through 45 inclusive.
- Scheduled demand: for each week, add `Standard Return Intake Hours` and `Exception Review Hours` on sheet `Returns`, and ignore `Illustrative Total - Do Not Use`.
- Initial condition at Week 3: `Start of Week Queue + Scheduled Demand = 467.20`.
- Production rate: 32 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.


## Required policy (deterministic)

For each week in order:

1. `Start of Week Queue = max(0, prior week End of Week Queue/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior week End of Week Queue/Buffer` (Week 3 starts from the initial condition).
3. Choose the day count for the week:
   - If reported `Start of Week Queue > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (32 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Week Queue <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 128.00`, else choose 5.
4. `Weekly Capacity = 32 * Days Worked`
5. `End of Week Queue/Buffer = Calc Start + Scheduled Demand - Weekly Capacity`
6. `Overtime Hours = 9 * max(0, Days Worked - 4)`

## Workbook format requirements

The output workbook must contain a worksheet named `Plan`.
Use exactly these headers in row 1:

1. `Week`
2. `Processing Days`
3. `Forecast Return Intake (Work Hrs)`
4. `Weekly Processing Capacity (Work Hrs)`
5. `Start-of-Week Return Queue (Work Hrs)`
6. `End-of-Week Return Queue/Buffer (Work Hrs)`
7. `Flex Shift Hours`

Add one row per week for Weeks 3..45 (43 rows total), in ascending week order with no gaps or duplicates.

## Summary file format

Create `/root/returns_throughput_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <week-number-or-N/A>`
2. `First_Week_4_Days: <week-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down week numbers (or `N/A` if not reached).
- The summary text must include the exact phrase(s): `Project CleanSweep`, `Milestone`.
