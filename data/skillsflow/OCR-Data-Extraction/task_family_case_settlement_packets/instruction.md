## Task description

Under `/app/workspace/dataset/cases`, there are nested case folders containing mixed document images.
Some images are purchase receipts, some are credit notes, and some are cover/checklist/admin pages that should not be included in the final output.

Recursively scan all image files under `/app/workspace/dataset/cases`, keep only the purchase receipts and credit notes, and write the final workbook to `/app/workspace/case_settlement.xlsx`.

The output workbook must contain exactly two sheets: `events` and `net_summary`.

### Sheet `events`
This sheet must have exactly these columns in this order:
- `case_id`
- `relative_path`
- `document_type`
- `document_ref`
- `date`
- `amount`

Column meanings:
- `case_id`: the first directory name under `/app/workspace/dataset/cases`
- `relative_path`: the image path relative to `/app/workspace/dataset/cases`, using forward slashes
- `document_type`: either `purchase` or `credit`
- `document_ref`: extracted reference such as receipt number or credit number
- `date`: document date in ISO format `YYYY-MM-DD`
- `amount`: extracted amount as a string with exactly two decimal places

Additional rules for `events`:
- Include only purchase receipts and credit notes
- Ignore cover sheets, checklists, thank-you pages, and other admin pages
- Sort rows by `case_id`, then by `relative_path`
- If the same `document_ref` appears more than once anywhere in the dataset, keep only the first occurrence by `relative_path` order and exclude later duplicates
- If a target document is missing a field, leave only that field empty

### Sheet `net_summary`
This sheet must have exactly these columns in this order:
- `case_id`
- `purchase_total`
- `credit_total`
- `net_amount`
- `latest_date`

Column meanings:
- `purchase_total`: sum of kept purchase amounts for that case
- `credit_total`: sum of kept credit amounts for that case
- `net_amount`: `purchase_total - credit_total`
- `latest_date`: latest kept document date in that case, in ISO format `YYYY-MM-DD`

Additional rules for `net_summary`:
- Include exactly one row per `case_id` that has at least one kept target document
- Sort rows by `case_id` ascending
- Format all monetary totals as strings with exactly two decimal places

## Extraction guidelines

### Purchase receipts
Treat a document as a purchase document if it contains one of:
- `PURCHASE RECEIPT`
- `TAX INVOICE`
- `STORE RECEIPT`

Use these amount keywords for purchase documents:
- `GRAND TOTAL`
- `TOTAL DUE`
- `AMOUNT DUE`

### Credit notes
Treat a document as a credit document if it contains one of:
- `CREDIT NOTE`
- `REFUND ADJUSTMENT`
- `CREDIT MEMO`

Use these amount keywords for credit documents:
- `CREDIT AMOUNT`
- `REFUND TOTAL`
- `TOTAL CREDIT`

### Reference and date
Look for reference labels such as:
- `Receipt No`
- `Credit No`
- `Reference`

Look for date labels such as:
- `Issue Date`
- `Date`

Dates may appear as:
- `DD/MM/YYYY`
- `DD-MM-YYYY`
- `MM/DD/YYYY`
- `YYYY-MM-DD`

If a date is ambiguous, prefer `DD/MM/YYYY`.

Ignore lines containing:
- `SUBTOTAL`
- `TAX`
- `DISCOUNT`

Some documents place the amount keyword on one line and the number on the next line.

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (`tesseract-ocr`)
- `pytesseract`
- `Pillow`
- `openpyxl`
