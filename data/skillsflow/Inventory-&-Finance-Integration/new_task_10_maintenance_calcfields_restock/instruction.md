You are a reliability planning analyst in manufacturing maintenance.

Build a single Excel workbook at:

- /root/maintenance_resupply_actions_sep_2025.xlsx

Use this source workbook:

- /root/Maintenance_Parts_and_Deliveries_Latest.xlsx

Source workbook sheets:

- Current Parts
- Scheduled Deliveries
- Ratio

Important Harbor adaptation:

- Use explicit boolean fields instead of visual highlighting so verification is fully programmatic.

Create exactly two sheets in this order:

1. Part_Results
2. Additional_Resupply_Needed

## Sheet 1: Part_Results

Populate metadata cells:

- A1=Field, B1=Value
- A2=AsOfDate, B2=<YYYY-MM-DD>
- A3=PlanningHorizonEnd, B3=<YYYY-MM-DD>
- A4=RemainingDaysInSeptember, B4=<integer>

Place this header row at row 6:

1. Part_Code
2. Current_Units
3. Daily_Consumption_Units
4. Current_DOH
5. Projected_Stockout_Date
6. Inbound_Units_By_Sep30
7. Delivered_DOH_To_Sep30
8. Remaining_September_Demand_Units
9. Additional_Units_Needed
10. Crates_Required_Rounded_Up
11. Required_Delivery_Date
12. Rounding_Applied
13. Earlier_Delivery_Required
14. Earliest_Scheduled_Delivery_Date

One row per entity from Current Parts, preserving source order.

Calculation rules:

- AsOfDate = date in Current Parts!B1
- PlanningHorizonEnd = date in Current Parts!D1
- RemainingDaysInSeptember = calendar day difference (PlanningHorizonEnd - AsOfDate)
- Current_DOH = Current_Units / Daily_Consumption_Units when rate > 0, else blank
- Projected_Stockout_Date = AsOfDate + floor(Current_DOH) when rate > 0, else blank
- Inbound_Units_By_Sep30 = sum of inbound quantity for that entity where inbound date <= PlanningHorizonEnd
- Delivered_DOH_To_Sep30 = (Current_Units + Inbound_Units_By_Sep30) / Daily_Consumption_Units when rate > 0, else blank
- Remaining_September_Demand_Units = Daily_Consumption_Units * RemainingDaysInSeptember
- Additional_Units_Needed = max(0, Remaining_September_Demand_Units - Current_Units - Inbound_Units_By_Sep30)
- Crates_Required_Rounded_Up = ceil(Additional_Units_Needed / conversion ratio in Ratio) when additional > 0, else 0
- Earliest_Scheduled_Delivery_Date = earliest scheduled inbound date for the entity, else blank
- Required_Delivery_Date:
  - blank when Crates_Required_Rounded_Up = 0
  - else if Earliest_Scheduled_Delivery_Date <= Projected_Stockout_Date, use AsOfDate + floor(Delivered_DOH_To_Sep30)
  - else use Projected_Stockout_Date
- Rounding_Applied = TRUE when additional > 0 and rounding changed container count; else FALSE
- Earlier_Delivery_Required = TRUE when containers > 0 and (Earliest_Scheduled_Delivery_Date blank OR Required_Delivery_Date < Earliest_Scheduled_Delivery_Date); else FALSE

Date fields must be ISO strings (YYYY-MM-DD) in projected/required/earliest date columns.

## Sheet 2: Additional_Resupply_Needed

Header row at row 1:

1. Part_Code
2. Required_Delivery_Date
3. Crates_Required_Rounded_Up
4. Additional_Units_Needed
5. Rounding_Applied
6. Earlier_Delivery_Required

Include only rows where Crates_Required_Rounded_Up > 0, with each entity once and in the same order as Part_Results.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the .xlsx file at the required output path.
