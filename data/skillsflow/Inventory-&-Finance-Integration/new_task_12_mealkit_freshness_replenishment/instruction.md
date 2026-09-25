You are a fulfillment planning analyst in perishable meal-kit distribution.

Build a single Excel workbook at:

- /root/freshness_replenishment_plan_november_2025.xlsx

Use this source workbook:

- /root/MealKits_Inventory_and_Inbound_Latest.xlsx

Source workbook sheets:

- Current Inventory
- Incoming Deliveries
- Shelf_Life

Important Harbor adaptation:

- Use explicit boolean fields instead of visual highlighting so verification is fully programmatic.

Create exactly two sheets in this order:

1. Freshness_Results
2. Additional_Freshness_Needed

## Sheet 1: Freshness_Results

Populate metadata cells:

- A1=Field, B1=Value
- A2=AsOfDate, B2=<YYYY-MM-DD>
- A3=PlanningHorizonEnd, B3=<YYYY-MM-DD>
- A4=RemainingDaysInNovember, B4=<integer>

Place this header row at row 6:

1. Meal_Kit_ID
2. Current_Boxes
3. Boxes_Expiring_By_Nov30
4. Usable_Current_Boxes
5. Daily_Order_Rate_Boxes
6. Current_DOH
7. Projected_OOS_Date
8. Inbound_Boxes_By_Nov30
9. Delivered_DOH_To_Nov30
10. Remaining_November_Demand_Boxes
11. Additional_Boxes_Needed
12. Pallets_Required_Rounded_Up
13. Required_Delivery_Date
14. Rounding_Applied
15. Earlier_Delivery_Required
16. Earliest_Scheduled_Inbound_Date

One row per entity from Current Inventory, preserving source order.

Calculation rules:

- AsOfDate = date in Current Inventory!B1
- PlanningHorizonEnd = date in Current Inventory!D1
- RemainingDaysInNovember = calendar day difference (PlanningHorizonEnd - AsOfDate)
- Current_DOH = Current_Boxes / Daily_Order_Rate_Boxes when rate > 0, else blank
- Projected_OOS_Date = AsOfDate + floor(Current_DOH) when rate > 0, else blank
- Inbound_Boxes_By_Nov30 = sum of inbound quantity for that entity where inbound date <= PlanningHorizonEnd
- Delivered_DOH_To_Nov30 = (Current_Boxes + Inbound_Boxes_By_Nov30) / Daily_Order_Rate_Boxes when rate > 0, else blank
- Remaining_November_Demand_Boxes = Daily_Order_Rate_Boxes * RemainingDaysInNovember
- Usable_Current_Boxes = max(0, Current_Boxes - Boxes_Expiring_By_Nov30)
- Current_DOH = Usable_Current_Boxes / Daily_Order_Rate_Boxes when rate > 0, else blank
- Delivered_DOH_To_Nov30 = (Usable_Current_Boxes + Inbound_Boxes_By_Nov30) / Daily_Order_Rate_Boxes when rate > 0, else blank
- Additional_Boxes_Needed = max(0, Remaining_November_Demand_Boxes - Usable_Current_Boxes - Inbound_Boxes_By_Nov30)
- Pallets_Required_Rounded_Up = ceil(Additional_Boxes_Needed / conversion ratio in Shelf_Life) when additional > 0, else 0
- Earliest_Scheduled_Inbound_Date = earliest scheduled inbound date for the entity, else blank
- Required_Delivery_Date:
  - blank when Pallets_Required_Rounded_Up = 0
  - else if Earliest_Scheduled_Inbound_Date <= Projected_OOS_Date, use AsOfDate + floor(Delivered_DOH_To_Nov30)
  - else use Projected_OOS_Date
- Rounding_Applied = TRUE when additional > 0 and rounding changed container count; else FALSE
- Earlier_Delivery_Required = TRUE when containers > 0 and (Earliest_Scheduled_Inbound_Date blank OR Required_Delivery_Date < Earliest_Scheduled_Inbound_Date); else FALSE

Date fields must be ISO strings (YYYY-MM-DD) in projected/required/earliest date columns.

## Sheet 2: Additional_Freshness_Needed

Header row at row 1:

1. Meal_Kit_ID
2. Required_Delivery_Date
3. Pallets_Required_Rounded_Up
4. Additional_Boxes_Needed
5. Rounding_Applied
6. Earlier_Delivery_Required

Include only rows where Pallets_Required_Rounded_Up > 0, with each entity once and in the same order as Freshness_Results.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the .xlsx file at the required output path.
