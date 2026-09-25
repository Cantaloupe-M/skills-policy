You are a chemical processing operations supervisor building a catch-up plan for reactor crew capacity.

Use `/root/chemical_demand.json` and generate two deliverables:

1. `/root/chemical_schedule_plan.xlsx`
2. `/root/chemical_schedule_summary.txt`

## Data to use

- Phases: 10 through 58 inclusive.
- The JSON is a list of objects. Each object has the structure `{"week": N, "data": {"demand_per_week": float or null}, "priority": "HIGH"|"MED"|"LOW"|"NORMAL"}`.
- Some weeks appear more than once in the list. **Use the first valid (non-null) occurrence** of each week — skip any entries with null demand values.
- Initial condition at Phase 10: `Start of Phase Past Due + Scheduled Demand = 1453.06`.
- Production rate: 40 standard hours per day.
- Days worked must be integers in `{4, 5, 6}`.

## Required policy (deterministic)

For each phase in order:

1. `Start of Phase Past Due (Std Hrs) = max(0, prior phase End of Phase Backlog/Buffer)` for reporting only.
2. Use the signed carryover value for calculations:
   - `Calc Start = prior phase End of Phase Backlog/Buffer` (Phase 10 starts from the initial condition).
3. Choose `Days Worked`:
   - If reported `Start of Phase Past Due > 0.01`, choose the smallest value in `{5, 6}` such that:
     - `Calc Start + Scheduled Demand - (40 * Days Worked) <= 0`
     - If neither 5 nor 6 satisfies this, choose 6.
   - Otherwise (`Start of Phase Past Due <= 0.01`):
     - Choose 4 if `Scheduled Demand <= 160`, else choose 5.
4. `Weekly Capacity (Std Hrs) = 40 * Days Worked`
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

Add one row per phase for Phases 10..58 (49 rows total), in ascending phase order with no gaps/duplicates.

## Summary file format

Create `/root/chemical_schedule_summary.txt` with exactly 3 lines:

1. `First_Week_5_Days: <phase-number-or-N/A>`
2. `First_Week_4_Days: <phase-number-or-N/A>`
3. `Summary: <manager-facing summary>`

The summary text must be no more than 60 words and no more than 3 sentences, and it must mention both step-down phase numbers (or `N/A` if not reached).
