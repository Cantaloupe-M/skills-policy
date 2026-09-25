## Task description

In `/app/workspace/dataset/img`, there are 15 scanned invoice images. Each invoice contains text such as invoice date, vendor name, and total amount. The text consists of digits and English characters.

Read all image files under the given path, extract the invoice date and total amount from each image, and write the results into an Excel file `/app/workspace/invoice_summary.xlsx`.

The output Excel file must:
- Contain exactly one sheet named "invoices"
- Have 3 columns in this order: `filename`, `date`, `total_amount`
  - `filename`: the source filename (e.g., "inv_001.jpg")
  - `date`: the invoice date in ISO format YYYY-MM-DD
  - `total_amount`: the monetary value as a string with exactly two decimal places (e.g., "1250.50")
- If extraction fails for any field, set it to null (empty cell)
- The first row must be the column headers
- Data rows must be ordered by filename in ascending order
- No extra columns, rows, or sheets

## Extraction guidelines

Look for the total amount by finding lines containing these keywords (priority from highest to lowest):
- GRAND TOTAL
- TOTAL DUE
- AMOUNT DUE
- TOTAL
- AMOUNT

Skip lines that also contain these exclusion keywords:
- SUBTOTAL
- SUB TOTAL
- TAX
- GST
- DISCOUNT
- CHANGE

The total amount may include comma separators (e.g., 1,234.56) or currency symbols. Extract only the numeric value.

For dates, common formats on the invoices include:
- DD/MM/YYYY
- MM/DD/YYYY
- DD-MM-YYYY
- YYYY-MM-DD

Convert all dates to ISO format (YYYY-MM-DD). If a date appears ambiguous (e.g., 01/02/2024), prefer the DD/MM/YYYY interpretation.

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (tesseract-ocr)
- pytesseract
- Pillow (PIL)
- openpyxl
