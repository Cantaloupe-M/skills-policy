You are a sales and inventory planning analyst for a beverage distributor.

Build a single Excel workbook at:

- `/root/additional_shipments_needed_updated_july_2025.xlsx`

Use this source workbook:

- `/root/Inventory_and_Shipments_Latest.xlsx`

The source workbook has:

- `Current Inventory` sheet (AsOfDate, Month End, SKU inventory, daily rate)
- `Incoming Shipments` sheet (scheduled deliveries)
- `Ratio` sheet (cases-per-pallet conversion)

Important adaptation for this Harbor task:

- Instead of visual highlighting, use explicit boolean fields so verification is fully programmatic.

Create exactly two sheets in this order:

1. `SKU_Results`
2. `Additional_Shipments_Needed`

## Sheet 1: `SKU_Results`

Populate fixed metadata cells:

- `A1=Field`, `B1=Value`
- `A2=AsOfDate`, `B2=<YYYY-MM-DD>`
- `A3=PlanningHorizonEnd`, `B3=<YYYY-MM-DD>`
- `A4=RemainingDaysInJuly`, `B4=<integer>`

Place this header row at row 6 (A6:N6):

1. `Product_SKU`
2. `Current_Cases`
3. `Daily_Rate_Cases_Per_Day`
4. `Current_DOH`
5. `Projected_OOS_Date`
6. `Inbound_Cases_By_July31`
7. `Delivered_DOH_To_July31`
8. `Remaining_July_Demand_Cases`
9. `Additional_Cases_Needed`
10. `Pallets_Required_Rounded_Up`
11. `Required_Delivery_Date`
12. `Rounding_Applied`
13. `Earlier_Delivery_Required`
14. `Earliest_Scheduled_Inbound_Date`

One row per SKU from `Current Inventory`, preserving source order.

Calculation rules:

- `AsOfDate` = date in `Current Inventory!B1`
- `PlanningHorizonEnd` = date in `Current Inventory!D1`
- `RemainingDaysInJuly` = calendar day difference `(PlanningHorizonEnd - AsOfDate)` (for July 4 to July 31 this is `27`)
- `Current_DOH` = `Current_Cases / Daily_Rate_Cases_Per_Day` when rate > 0, else blank
- `Projected_OOS_Date` = `AsOfDate + floor(Current_DOH)` when rate > 0, else blank
- `Inbound_Cases_By_July31` = sum of `Number of Cases Left` for that SKU where shipment `Delivery Date <= PlanningHorizonEnd`
- `Delivered_DOH_To_July31` = `(Current_Cases + Inbound_Cases_By_July31) / Daily_Rate_Cases_Per_Day` when rate > 0, else blank
- `Remaining_July_Demand_Cases` = `Daily_Rate_Cases_Per_Day * RemainingDaysInJuly`
- `Additional_Cases_Needed` = `max(0, Remaining_July_Demand_Cases - Current_Cases - Inbound_Cases_By_July31)`
- `Pallets_Required_Rounded_Up` = `ceil(Additional_Cases_Needed / Cases_Per_Pallet)` when additional cases > 0, else `0`
- `Earliest_Scheduled_Inbound_Date` = earliest shipment date listed for the SKU in `Incoming Shipments`, else blank
- `Required_Delivery_Date`:
  - blank when `Pallets_Required_Rounded_Up = 0`
  - else if `Earliest_Scheduled_Inbound_Date <= Projected_OOS_Date`, use `AsOfDate + floor(Delivered_DOH_To_July31)`
  - else use `Projected_OOS_Date`
- `Rounding_Applied` = `TRUE` when additional cases > 0 and rounding up changed the pallet value; else `FALSE`
- `Earlier_Delivery_Required` = `TRUE` when pallets required > 0 and (`Earliest_Scheduled_Inbound_Date` is blank OR `Required_Delivery_Date < Earliest_Scheduled_Inbound_Date`); else `FALSE`

Date fields must be ISO strings (`YYYY-MM-DD`) in columns `E`, `K`, and `N`.

## Sheet 2: `Additional_Shipments_Needed`

Header row at row 1 (A1:F1):

1. `Product_SKU`
2. `Required_Delivery_Date`
3. `Pallets_Required_Rounded_Up`
4. `Additional_Cases_Needed`
5. `Rounding_Applied`
6. `Earlier_Delivery_Required`

Include only rows where `Pallets_Required_Rounded_Up > 0`, with each SKU appearing once and in the same order as `SKU_Results`.

Constraints:

- Keep numeric fields numeric.
- Do not modify source input files.
- Final answer must be the `.xlsx` file at the required output path.
