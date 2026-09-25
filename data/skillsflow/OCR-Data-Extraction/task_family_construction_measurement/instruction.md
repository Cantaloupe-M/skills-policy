## Task description

In `/app/workspace/dataset/img`, there are 12 scanned construction measurement forms. Each form contains:
- Project code (e.g., PROJ-2024-001)
- Measurement date
- Item descriptions with quantities, units, and unit prices
- Total amount for the project

Read all image files, extract the data, and write the results into an Excel file `/app/workspace/construction_summary.xlsx`.

The output Excel file must contain TWO sheets:

### Sheet 1: "details"
Contains individual line items from all forms:
- 5 columns in this order: `filename`, `project_code`, `item_description`, `quantity`, `unit_price`
  - `filename`: the source filename (e.g., "meas_001.jpg")
  - `project_code`: the project identifier
  - `item_description`: description of the measured item
  - `quantity`: the quantity as a string (may be integer or decimal, e.g., "10" or "15.5")
  - `unit_price`: the unit price as a string with exactly two decimal places (e.g., "125.00")
- If extraction fails for any field, set it to null (empty cell)
- The first row must be column headers
- Data rows must be ordered by filename, then by item order within each form

### Sheet 2: "summary"
Contains the total amount per project:
- 3 columns in this order: `project_code`, `date`, `total_amount`
  - `project_code`: the project identifier
  - `date`: the measurement date in ISO format YYYY-MM-DD
  - `total_amount`: the total amount for that project as a string with exactly two decimal places
- If extraction fails for any field, set it to null (empty cell)
- The first row must be column headers
- Data rows must be ordered by project_code in ascending order
- Each project should appear only once

## Extraction guidelines

### Project code
Look for labels like:
- PROJECT, PROJECT CODE, PROJ, PROJECT NO, PROJECT ID
- Format: PROJ-YYYY-NNN (e.g., PROJ-2024-001)

### Date
Measurement dates may appear as:
- DATE, MEASUREMENT DATE, MEAS. DATE, MEAS DATE
- Formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD

### Item details
Construction forms typically have tabular structures:
- Item descriptions may span multiple words
- Quantity may be followed by unit (m, m², m³, pcs, kg, etc.)
- Unit price is usually the last numeric column before total

Look for patterns like:
```
Item Description        Qty    Unit Price
Concrete C30            50     150.00
Steel reinforcement     100    12.50
```

### Total amount
Project totals appear with keywords:
- PROJECT TOTAL, TOTAL, GRAND TOTAL, SUBTOTAL (but use the final/grand total)
- May be handwritten or printed

### Handwritten annotations
Some forms contain handwritten notes or corrections. These may be harder to OCR. Try multiple preprocessing strategies.

## Pre-installed libraries

The following libraries are already installed:
- Tesseract OCR (tesseract-ocr)
- pytesseract
- Pillow (PIL)
- openpyxl
