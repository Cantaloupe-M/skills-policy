Read the product catalog from `/root/product_catalog.pdf` and the sales transaction data from `/root/sales_transactions.xlsx`, then create a new report called `/root/product_sales_report.xlsx`.

The product catalog PDF contains columns: PRODUCT_ID, PRODUCT_NAME, CATEGORY, UNIT_COST, UNIT_PRICE.
The sales transactions XLSX contains columns: TRANSACTION_ID, PRODUCT_ID, REGION, MONTH, QUARTER, QUANTITY, UNIT_PRICE.

Before building pivots, reconcile the transaction export:
- Trim whitespace in text fields and normalize REGION / MONTH / QUARTER casing so the final report uses canonical labels.
- Drop rows with a missing PRODUCT_ID, an unknown PRODUCT_ID, or a non-positive QUANTITY.
- If UNIT_PRICE is missing in a transaction row, fill it from the product catalog; if both values exist, keep the transaction UNIT_PRICE.
- Remove exact duplicate transaction rows after the cleanup above.

Join the cleaned transactions to the catalog on PRODUCT_ID. Then create a new Excel file with four pivot table sheets and one source data sheet (five sheets total):

1. "Revenue by Category"
This sheet contains a pivot table with:
Rows: CATEGORY
Values: Sum of REVENUE (where REVENUE = QUANTITY × UNIT_PRICE from the transactions)

2. "Units by Region"
This sheet contains a pivot table with:
Rows: REGION
Values: Sum of QUANTITY

3. "Products by Category"
This sheet contains a pivot table with:
Rows: CATEGORY
Values: Count (number of distinct transactions)

4. "Category Region Matrix"
This sheet contains a pivot table with:
Rows: CATEGORY
Columns: REGION
Values: Sum of REVENUE

5. "SourceData"
This sheet contains the cleaned, joined data enriched with:
- REVENUE: QUANTITY × UNIT_PRICE
- PROFIT: REVENUE - (QUANTITY × UNIT_COST)
- MARGIN_PCT: PROFIT / REVENUE (as a decimal between 0 and 1)
- PRICE_STATUS: `catalog_price` when UNIT_PRICE was filled from the catalog, otherwise `transaction_override`
- CATALOG_MATCH_STATUS: `matched` for every retained row
- RECONCILIATION_ACTION: one of `filled_unit_price_from_catalog`, `used_transaction_unit_price`, or `none` if no special action was needed

Save the final results in `/root/product_sales_report.xlsx`
