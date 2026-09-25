## Task description

In `/app/workspace/dataset/img`, there are 20 scanned e-commerce shipping order images. Each order contains:
- Order date
- Order ID (unique identifier)
- Item details with quantity and unit price
- Total amount

Read all image files, extract the data, and write the results into an Excel file `/app/workspace/orders_summary.xlsx`.

The output Excel file must:
- Contain exactly one sheet named "orders"
- Have 4 columns in this order: `filename`, `order_id`, `date`, `total_amount`
  - `filename`: the source filename (e.g., "order_001.jpg")
  - `order_id`: the order identifier (alphanumeric, e.g., "ORD-2024-00123")
  - `date`: the order date in ISO format YYYY-MM-DD
  - `total_amount`: the total amount as a string with exactly two decimal places (e.g., "156.78")
- If extraction fails for any field, set it to null (empty cell)
- The first row must be the column headers
- Data rows must be ordered by filename in ascending order
- No extra columns, rows, or sheets

Additionally, there is a reference file `/app/workspace/dataset/known_orders.csv` that contains a list of known valid order IDs. You should:
- Verify that each extracted order_id exists in this reference file
- If an order_id is NOT in the reference file, set order_id to null (but keep the filename, date, and total_amount)

## Extraction guidelines

### Order ID
Order IDs typically appear with labels like:
- ORDER ID, Order No., ORDER NO, Order Number, ORDER#
- Format examples: ORD-2024-00123, SO-2024-456, INV-789456

### Date
Dates may appear in various formats:
- ORDER DATE, Date, Order Date
- DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD

### Total amount
Look for:
- TOTAL, GRAND TOTAL, ORDER TOTAL, TOTAL DUE, AMOUNT DUE
- May include currency symbols: $, RM, MYR

Skip lines containing:
- SUBTOTAL, SUB TOTAL, TAX, GST, SHIPPING, DELIVERY FEE, DISCOUNT

Some orders may have the total split across multiple lines (keyword on one line, amount on the next).

### Duplicate handling
Some images may be duplicates (same order_id appears in multiple files). In such cases:
- Keep only the FIRST occurrence (by filename order)
- Mark subsequent duplicates by setting all fields to null except filename

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (tesseract-ocr)
- pytesseract
- Pillow (PIL)
- openpyxl
