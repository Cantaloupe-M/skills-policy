You are a workforce planning analyst in hospital operations.

Build a single Excel workbook at:

- /root/additional_shift_blocks_needed_august_2025.xlsx

Use this source workbook:

- /root/Staffing_and_Shifts_Latest.xlsx

Source workbook sheets:

- Current Staffing
- Incoming Shifts
- Ratio

Important Harbor adaptation:

- Use explicit boolean fields instead of visual highlighting so verification is fully programmatic.

Create exactly two sheets in this order:

1. Unit_Results
2. Additional_Shifts_Needed

## Sheet 1: Unit_Results

Populate metadata cells:

- A1=Field, B1=Value
- A2=AsOfDate, B2=<YYYY-MM-DD>
- A3=PlanningHorizonEnd, B3=<YYYY-MM-DD>
- A4=RemainingDaysInAugust, B4=<integer>

Place this header row at row 6:

1. Care_Unit
2. Current_Staff_Hours
3. Daily_Required_Hours
4. Current_Coverage_Days
5. Projected_Understaff_Date
6. Incoming_Hours_By_Aug31
7. Delivered_Coverage_To_Aug31
8. Remaining_August_Demand_Hours
9. Additional_Hours_Needed
10. Shift_Blocks_Required_Rounded_Up
11. Required_Shift_Start_Date
12. Rounding_Applied
13. Earlier_Shift_Required
14. Earliest_Scheduled_Shift_Date

One row per entity from Current Staffing, preserving source order.

Calculation rules:

- AsOfDate = date in Current Staffing!B1
- PlanningHorizonEnd = date in Current Staffing!D1
- RemainingDaysInAugust = calendar day difference (PlanningHorizonEnd - AsOfDate)
- Current_Coverage_Days = Current_Staff_Hours / Daily_Required_Hours when rate > 0, else blank
- Projected_Understaff_Date = AsOfDate + floor(Current_Coverage_Days) when rate > 0, else blank
- Incoming_Hours_By_Aug31 = sum of inbound quantity for that entity where inbound date <= PlanningHorizonEnd
- Delivered_Coverage_To_Aug31 = (Current_Staff_Hours + Incoming_Hours_By_Aug31) / Daily_Required_Hours when rate > 0, else blank
- Remaining_August_Demand_Hours = Daily_Required_Hours * RemainingDaysInAugust
- Additional_Hours_Needed = max(0, Remaining_August_Demand_Hours - Current_Staff_Hours - Incoming_Hours_By_Aug31)
- Shift_Blocks_Required_Rounded_Up = ceil(Additional_Hours_Needed / conversion ratio in Ratio) when additional > 0, else 0
- Earliest_Scheduled_Shift_Date = earliest scheduled inbound date for the entity, else blank
- Required_Shift_Start_Date:
  - blank when Shift_Blocks_Required_Rounded_Up = 0
  - else if Earliest_Scheduled_Shift_Date <= Projected_Understaff_Date, use AsOfDate + floor(Delivered_Coverage_To_Aug31)
  - else use Projected_Understaff_Date
- Rounding_Applied = TRUE when additional > 0 and rounding changed container count; else FALSE
- Earlier_Shift_Required = TRUE when containers > 0 and (Earliest_Scheduled_Shift_Date blank OR Required_Shift_Start_Date < Earliest_Scheduled_Shift_Date); else FALSE

Date fields must be ISO strings (YYYY-MM-DD) in projected/required/earliest date columns.

## Sheet 2: Additional_Shifts_Needed

Header row at row 1:

1. Care_Unit
2. Required_Shift_Start_Date
3. Shift_Blocks_Required_Rounded_Up
4. Additional_Hours_Needed
5. Rounding_Applied
6. Earlier_Shift_Required

Include only rows where Shift_Blocks_Required_Rounded_Up > 0, with each entity once and in the same order as Unit_Results.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the .xlsx file at the required output path.
