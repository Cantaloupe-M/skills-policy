You are supporting an outbound-operations audit for carton handoff accuracy.

You are given three files:
- `/root/Manifest_Plan.xlsx`
- `/root/Dock_Scan_Log.xlsx`
- `/root/Outbound_Audit_Template.xlsx`

## Deliverables
Create both files below:
1. `/root/Outbound_Load_Audit.xlsx`
2. `/root/Outbound_Load_Brief.docx`

## Excel Requirements
Start from `/root/Outbound_Audit_Template.xlsx` and save the completed workbook as `/root/Outbound_Load_Audit.xlsx`.

The final workbook must keep the existing `Overview` worksheet unchanged and must also contain these populated worksheets:
- `RawData`
- `Formatted Data`
- `Summary`

### 1) `RawData`
- Copy the manifest plan table from `Manifest_Plan.xlsx` exactly.

### 2) `Formatted Data`
- Keep the same row order as `RawData`.
- Keep the first 8 columns exactly as:
  1. Shipment ID
  2. Carton ID
  3. Planned Zone
  4. Route
  5. Expected Weight
  6. Hazmat Flag
  7. Carrier
  8. Wave
- Add four new columns (columns 9-12) with exactly these headers:
  9. Missing Load Scan
  10. Zone Mismatch
  11. Total Errors
  12. Error Summary

To derive scan status, use `Dock_Scan_Log.xlsx` and keep only the latest row with `Status = LOADED` for each `(Shipment ID, Carton ID)`. Ignore other statuses when selecting the kept scan.

Use these rules:
- `Missing Load Scan` = 1 if no kept `LOADED` scan exists for that `(Shipment ID, Carton ID)`, else 0.
- `Zone Mismatch` = 1 if a kept `LOADED` scan exists and `Scanned Zone` != `Planned Zone`, else 0.
- `Total Errors` = `Missing Load Scan + Zone Mismatch`.
- `Error Summary` must be exactly one of:
  - `None`
  - `Missing Load Scan`
  - `Zone Mismatch`
  - `Missing Load Scan, Zone Mismatch`

For deterministic grading, write concrete numeric/text values in these added columns (do not rely on formulas requiring spreadsheet recalculation).

### 3) `Summary`
Create a drill-down summary table with exactly these headers:
1. Route
2. Shipment ID
3. Missing Load Scans
4. Zone Mismatches
5. Total Errors

Rules:
- Aggregate from `Formatted Data` by `(Route, Shipment ID)`.
- Include only groups where `Total Errors > 0`.
- Sort rows by `Route` ascending, then `Shipment ID` ascending.
- Append a final row with:
  - `Route` = `Grand Total`
  - `Shipment ID` = `-`
  - remaining columns = dataset totals.

## Word Summary Requirements
Create `/root/Outbound_Load_Brief.docx` with a short executive summary (3-6 sentences) that includes:
- A plain-language definition of both checks (`Missing Load Scan` and `Zone Mismatch`).
- The computed totals for Missing Load Scans, Zone Mismatches, and Total Errors.
- At least one actionable recommendation.
- Mention at least two high-priority shipment IDs with frequent exceptions.

## Important Constraints
- Preserve the `Overview` worksheet exactly as it appears in the template.
- Keep output filenames and worksheet names exactly as specified.
