## Task description

In `/app/workspace/dataset/img`, there are 16 scanned travel expense claim images.
A reference file `/app/workspace/dataset/claim_roster.csv` maps valid `claim_code` values to `employee_id` and `trip_id`.

Read all image files under the given path, extract the claim data, merge in the roster information, and write the final workbook to `/app/workspace/travel_claims.xlsx`.

The output workbook must:
- Contain exactly one sheet named `claims`
- Have exactly these columns in this order:
  - `filename`
  - `claim_code`
  - `employee_id`
  - `trip_id`
  - `date`
  - `total_amount`
- Use these meanings:
  - `filename`: source image filename
  - `claim_code`: extracted claim identifier from the image
  - `employee_id`: looked up from `claim_roster.csv`
  - `trip_id`: looked up from `claim_roster.csv`
  - `date`: transaction date in ISO format `YYYY-MM-DD`
  - `total_amount`: final reimbursable amount as a string with exactly two decimal places
- Order rows by filename ascending
- If `claim_code` is missing from the roster, keep the extracted `claim_code`, `date`, and `total_amount`, but leave `employee_id` and `trip_id` empty
- If any extracted field is missing, leave that specific cell empty
- Do not add extra sheets, rows, or columns

## Extraction guidelines

### Claim code
Look for labels such as:
- `Claim Code`
- `Claim Ref`
- `Expense Code`

The claim code format is like `CLM-2024-001`.

### Date
Look for labels such as:
- `Transaction Date`
- `Purchase Date`
- `Date`

Dates may appear as:
- `DD/MM/YYYY`
- `DD-MM-YYYY`
- `MM/DD/YYYY`
- `YYYY-MM-DD`

If a date is ambiguous, prefer `DD/MM/YYYY`.

### Final amount
Look for the final reimbursable amount using these keywords:
- `REIMBURSABLE TOTAL`
- `TOTAL CLAIM`
- `AMOUNT CLAIMED`
- `TOTAL DUE`

Ignore lines containing:
- `ADVANCE`
- `CASH PAID`
- `TIP`
- `TAX`

Some claims place the keyword on one line and the number on the next line.

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (`tesseract-ocr`)
- `pytesseract`
- `Pillow`
- `openpyxl`
