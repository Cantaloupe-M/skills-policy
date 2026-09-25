Read the product master list from `/root/product_info.pdf` and the inventory records from two warehouse files: `/root/warehouse_a_inventory.xlsx` and `/root/warehouse_b_inventory.xlsx`. Then create a consolidated inventory report at `/root/inventory_report.xlsx`.

The product info PDF contains columns: SKU, ITEM_NAME, CATEGORY, WEIGHT_KG, REORDER_LEVEL.
Both warehouse XLSX files contain columns: SKU, WAREHOUSE, QUANTITY_ON_HAND, LAST_RECEIVED, UNIT_VALUE.

Before building pivots, reconcile the data:
- Normalize SKU values by trimming whitespace, converting to uppercase, and removing internal spaces.
- Stack both warehouse files into one dataset.
- Drop rows where SKU is missing or not found in the product master list.
- Drop rows where QUANTITY_ON_HAND or UNIT_VALUE is missing or non-numeric.
- Remove exact duplicate inventory rows after cleanup.

Join with the product info on SKU. Then create a new Excel file with four pivot table sheets and one source data sheet (five sheets total):

1. "Stock by Category"
This sheet contains a pivot table with:
Rows: CATEGORY
Values: Sum of QUANTITY_ON_HAND

2. "Value by Warehouse"
This sheet contains a pivot table with:
Rows: WAREHOUSE
Values: Sum of TOTAL_VALUE (see SourceData enrichment below)

3. "Items by Category"
This sheet contains a pivot table with:
Rows: CATEGORY
Values: Count (number of inventory records)

4. "Category Warehouse Matrix"
This sheet contains a pivot table with:
Rows: CATEGORY
Columns: WAREHOUSE
Values: Sum of TOTAL_VALUE

5. "SourceData"
This sheet contains the cleaned, combined, and joined data enriched with:
- TOTAL_VALUE: QUANTITY_ON_HAND × UNIT_VALUE
- TOTAL_WEIGHT: QUANTITY_ON_HAND × WEIGHT_KG
- REORDER_FLAG: "Yes" if QUANTITY_ON_HAND < REORDER_LEVEL, otherwise "No"
- STOCK_STATUS: `at_risk` if QUANTITY_ON_HAND < REORDER_LEVEL, otherwise `healthy`
- VALUE_TIER: `low` if TOTAL_VALUE < 5000, `medium` if TOTAL_VALUE < 20000, otherwise `high`

Save the final results in `/root/inventory_report.xlsx`
