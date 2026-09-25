You are an electronics manufacturing supervisor building a catch-up plan for PCB assembly capacity.

Use `/root/assembly_schedule.xlsx` (sheet `Assembly`) and generate two deliverables:

1. `/root/assembly_plan.xlsx`
2. `/root/assembly_summary.txt`

## Data to use

- Phases: 6 through 54 inclusive.
- Scheduled demand: the column labeled `PCB Assembly Demand (Std Hrs)`. The source file may contain duplicate phase entries and extra columns — use only the first occurrence of each phase and only the demand column.
- Initial condition at Phase 6: `Start of Phase Past Due + Scheduled Demand = 469.59`.
- Production rate: 20 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.

## Required policy (deterministic)

For each phase in order:

1. `Start of Phase Past Due (Std Hrs) = max(0, prior phase End of Phase Backlog/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior phase End of Phase Backlog/Buffer` (Phase 6 starts from the initial condition).
3. Choose `Days Worked`:
   - If reported `Start of Phase Past Due > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (20 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Phase Past Due <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 80`, else choose 5.
4. `Weekly Capacity (Std Hrs) = 20 * Days Worked`
5. `End of Phase Backlog/Buffer (Std Hrs) = Calc Start + Scheduled Demand - Weekly Capacity`
6. `Overtime Hours = 10 * max(0, Days Worked - 4)`

## Workbook format requirements

Create a single worksheet named `Plan` with exactly these headers in row 1:

1. `Phase`
2. `Days Worked`
3. `Scheduled Demand (Std Hrs)`
4. `Weekly Capacity (Std Hrs)`
5. `Start of Phase Past Due (Std Hrs)`
6. `End of Phase Backlog/Buffer (Std Hrs)`
7. `Overtime Hours`

Add one row per phase for Phases 6..54 (49 rows total), in ascending phase order with no gaps/duplicates.

## Summary file format

Create `/root/assembly_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <phase-number-or-N/A>`
2. `First_Week_4_Days: <phase-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down phase numbers (or `N/A` if not reached).
