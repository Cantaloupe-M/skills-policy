## Task description

In `/app/workspace/dataset/img`, there are 14 scanned utility bill images.
A workbook template already exists at `/app/workspace/bill_tracker_template.xlsx`.

Read all image files under the given path, extract the bill date and amount due from each image, and update the template workbook.
Save the final workbook to `/app/workspace/bill_tracker_filled.xlsx`.

The output workbook must:
- Keep exactly the same two sheet names as the template: `cover` and `bills`
- Preserve the `cover` sheet content exactly as it is in the template
- Write the extracted rows into the `bills` sheet only
- Keep the `bills` header row exactly as `scan_name`, `bill_date`, `amount_due`
- Remove any placeholder or old data rows under that header before writing new rows
- Order the data rows by filename ascending
- Use these column meanings:
  - `scan_name`: source image filename
  - `bill_date`: bill date in ISO format `YYYY-MM-DD`
  - `amount_due`: amount due as a string with exactly two decimal places
- If extraction fails for a field, leave that cell empty
- Do not add extra sheets, columns, or rows outside the required data

## Extraction guidelines

### Date
Look for lines such as:
- `Statement Date`
- `Bill Date`
- `Date`

Dates may appear in these formats:
- `DD/MM/YYYY`
- `DD-MM-YYYY`
- `MM/DD/YYYY`
- `YYYY-MM-DD`

If a date is ambiguous, prefer `DD/MM/YYYY`.

### Amount due
Look for the final payable amount using these keywords, in priority order:
- `PAY THIS AMOUNT`
- `AMOUNT DUE`
- `TOTAL DUE`
- `CURRENT CHARGES`

Ignore lines containing these distractors:
- `PREVIOUS BALANCE`
- `LATE FEE`
- `TAX`
- `CREDIT`

Some bills place the keyword on one line and the number on the next line.
The amount may contain comma separators like `1,234.56`.

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (`tesseract-ocr`)
- `pytesseract`
- `Pillow`
- `openpyxl`
