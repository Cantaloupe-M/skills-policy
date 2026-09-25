## Task description

Under `/app/workspace/dataset`, there are nested batch folders containing mixed image packets.
Some images are fuel purchase receipts, while others are cover sheets, route notes, promotion pages, or loyalty forms.

Recursively scan all image files under `/app/workspace/dataset`, keep only the fuel purchase receipts, and write the final workbook to `/app/workspace/fuel_packets.xlsx`.

The output workbook must:
- Contain exactly one sheet named `transactions`
- Have exactly these columns in this order:
  - `batch_name`
  - `relative_path`
  - `txn_ref`
  - `date`
  - `total_amount`
- Use these meanings:
  - `batch_name`: the first directory name under `/app/workspace/dataset` for that image
  - `relative_path`: the image path relative to `/app/workspace/dataset`, using forward slashes
  - `txn_ref`: the transaction reference from the receipt
  - `date`: sale date in ISO format `YYYY-MM-DD`
  - `total_amount`: final paid amount as a string with exactly two decimal places
- Include only target fuel purchase receipts in the output
- Ignore cover sheets, route notes, promotion pages, and loyalty forms entirely
- Sort rows by `relative_path` ascending
- If the same `txn_ref` appears more than once anywhere in the dataset, keep only the first occurrence by `relative_path` order and exclude later duplicates from the output
- Do not add extra sheets, rows, or columns

## Extraction guidelines

### Target receipts
Treat an image as a target fuel receipt only if it contains one of these indicators:
- `FUEL RECEIPT`
- `PUMP SALE`
- `TAX INVOICE`

### Transaction reference
Look for labels such as:
- `Txn Ref`
- `Transaction No`
- `Ref No`

### Date
Look for labels such as:
- `Sale Date`
- `Date`

Dates may appear as:
- `DD/MM/YYYY`
- `DD-MM-YYYY`
- `MM/DD/YYYY`
- `YYYY-MM-DD`

If a date is ambiguous, prefer `DD/MM/YYYY`.

### Total amount
Look for the final paid amount using these keywords:
- `GRAND TOTAL`
- `TOTAL AMOUNT`
- `AMOUNT PAID`
- `TOTAL`

Ignore lines containing:
- `DISCOUNT`
- `CASHBACK`
- `SAVINGS`
- `LOYALTY`
- `TAX`

Some receipts place the keyword on one line and the number on the next line.

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (`tesseract-ocr`)
- `pytesseract`
- `Pillow`
- `openpyxl`
