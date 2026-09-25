You are a resilience planning analyst in datacenter backup-fuel planning.

Build a single Excel workbook at:

- /root/stochastic_refill_plan_october_2025.xlsx

Use this source workbook:

- /root/Backup_Fuel_and_Refills_Latest.xlsx

Source workbook sheets:

- Current Fuel
- Scheduled Refills
- Policy Parameters

Important Harbor adaptation:

- Use explicit boolean fields instead of visual highlighting so verification is fully programmatic.

Create exactly two sheets in this order:

1. Site_Results
2. Additional_Refills_Needed

## Sheet 1: Site_Results

Populate metadata cells:

- A1=Field, B1=Value
- A2=AsOfDate, B2=<YYYY-MM-DD>
- A3=PlanningHorizonEnd, B3=<YYYY-MM-DD>
- A4=RemainingDaysInOctober, B4=<integer>

Place this header row at row 6:

1. Site_ID
2. Current_Liters
3. Expected_Daily_Burn_Liters
4. Daily_Burn_StdDev
5. Current_DOH
6. Projected_Runout_Date
7. Inbound_Liters_By_Oct31
8. Delivered_DOH_To_Oct31
9. Remaining_October_Burn_Liters
10. Safety_Buffer_Liters
11. Additional_Liters_Needed
12. Tankers_Required_Rounded_Up
13. Required_Refill_Date
14. Rounding_Applied
15. Earlier_Refill_Required
16. Earliest_Scheduled_Refill_Date

One row per entity from Current Fuel, preserving source order.

Calculation rules:

- AsOfDate = date in Current Fuel!B1
- PlanningHorizonEnd = date in Current Fuel!D1
- RemainingDaysInOctober = calendar day difference (PlanningHorizonEnd - AsOfDate)
- Current_DOH = Current_Liters / Expected_Daily_Burn_Liters when rate > 0, else blank
- Projected_Runout_Date = AsOfDate + floor(Current_DOH) when rate > 0, else blank
- Inbound_Liters_By_Oct31 = sum of inbound quantity for that entity where inbound date <= PlanningHorizonEnd
- Delivered_DOH_To_Oct31 = (Current_Liters + Inbound_Liters_By_Oct31) / Expected_Daily_Burn_Liters when rate > 0, else blank
- Remaining_October_Burn_Liters = Expected_Daily_Burn_Liters * RemainingDaysInOctober
- Safety_Buffer_Liters = Service_Level_Z * Daily_Burn_StdDev * sqrt(RemainingDaysInOctober)
- Additional_Liters_Needed = max(0, Remaining_October_Burn_Liters + Safety_Buffer_Liters - Current_Liters - Inbound_Liters_By_Oct31)
- Tankers_Required_Rounded_Up = ceil(Additional_Liters_Needed / conversion ratio in Policy Parameters) when additional > 0, else 0
- Earliest_Scheduled_Refill_Date = earliest scheduled inbound date for the entity, else blank
- Required_Refill_Date:
  - blank when Tankers_Required_Rounded_Up = 0
  - else if Earliest_Scheduled_Refill_Date <= Projected_Runout_Date, use AsOfDate + floor(Delivered_DOH_To_Oct31)
  - else use Projected_Runout_Date
- Rounding_Applied = TRUE when additional > 0 and rounding changed container count; else FALSE
- Earlier_Refill_Required = TRUE when containers > 0 and (Earliest_Scheduled_Refill_Date blank OR Required_Refill_Date < Earliest_Scheduled_Refill_Date); else FALSE

Date fields must be ISO strings (YYYY-MM-DD) in projected/required/earliest date columns.

## Sheet 2: Additional_Refills_Needed

Header row at row 1:

1. Site_ID
2. Required_Refill_Date
3. Tankers_Required_Rounded_Up
4. Additional_Liters_Needed
5. Safety_Buffer_Liters
6. Rounding_Applied
7. Earlier_Refill_Required

Include only rows where Tankers_Required_Rounded_Up > 0, with each entity once and in the same order as Site_Results.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the .xlsx file at the required output path.
