## Task description

In `/app/workspace/dataset/img`, there are 18 photographed pharmacy shelf labels and price tags. Each image contains product information including:
- Product name
- Expiry date or manufacture date
- Price (may appear with different currency symbols: $, RM, MYR, or no symbol)

Read all image files under the given path, extract the date and price from each, and write the results into an Excel file `/app/workspace/pharmacy_prices.xlsx`.

The output Excel file must:
- Contain exactly one sheet named "products"
- Have 3 columns in this order: `filename`, `date`, `price`
  - `filename`: the source filename (e.g., "pharm_001.jpg")
  - `date`: the expiry or manufacture date in ISO format YYYY-MM-DD. If both dates appear, prefer the expiry date.
  - `price`: the price as a string with exactly two decimal places (e.g., "12.99")
- If extraction fails for any field, set it to null (empty cell)
- The first row must be the column headers
- Data rows must be ordered by filename in ascending order
- No extra columns, rows, or sheets

## Extraction guidelines

### Date extraction
Pharmacy labels use various date formats:
- EXP: DD/MM/YYYY, DD-MM-YYYY, MM/YYYY, MM-YYYY
- MFG: DD/MM/YYYY, DD-MM-YYYY, MM/YYYY
- Sometimes written as "EXPIRY:", "EXPIRES:", "MANUFACTURED:", "MFG DATE:"

Priority order for date selection:
1. EXPIRY/EXP date (highest priority)
2. EXPIRES date
3. MANUFACTURED/MFG date (lowest priority)

If only month/year is given (e.g., 12/2025), use the first day of that month (2025-12-01).

### Price extraction
Prices may appear in these formats:
- With currency symbols: $12.99, RM 12.99, MYR 12.99
- Without symbols: 12.99, 12.99 each
- With comma separators: 1,234.56

Look for keywords near the price:
- PRICE, PRICE:, RM, MYR, $
- TOTAL, TOTAL PRICE
- Labels ending with "EACH" often indicate unit price

### Noise handling
Pharmacy labels often have:
- Background colors and patterns
- Small text
- Stickers or overlays
- Handwritten annotations

Some images may be blurry or have low contrast. Try multiple OCR strategies.

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (tesseract-ocr)
- pytesseract
- Pillow (PIL)
- openpyxl
