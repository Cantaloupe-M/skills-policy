#!/bin/bash
set -euo pipefail

python3 - << 'PY'
from openpyxl import load_workbook

source_path = "/solution/Fulfillment_Recovery_Plan_Analysis.xlsx"
output_path = "/root/fulfillment_recovery_plan_analysis.xlsx"

wb = load_workbook(source_path)

for ws in wb.worksheets:
    if ws.max_row > 103:
        ws.delete_rows(104, ws.max_row - 103)

    ws["D4"] = 1065
    ws["G4"] = 855

    for row in range(4, 104):
        if ws.title == "10 hr Shift Relocate Bulk Stor":
            ws.cell(row=row, column=9).value = 0
        ws.cell(row=row, column=10).value = f"=C{row}+F{row}+I{row}"

wb.save(output_path)
print(f"Saved workbook to {output_path}")
PY

cat > /root/fulfillment_recovery_summary.md << 'EOF'
## Scenario 1
Actions: Kept bulk pallet processing in the main picking zone while operating one 8-hour shift, then moved to the 135 units/day rate after the February 5 capacity step-up.
Priority Express Orders Impact: Express order backlog is reduced but May demand is still open at the end of the planning horizon.
Standard Freight Orders Impact: Standard freight fulfillment starts later and May standard demand remains open by May 1.
Bulk Pallet Loads Impact: Bulk pallet cadence is maintained in this zone, but it consumes capacity needed for order fulfillment catch-up.
May PO On-Time: No

## Scenario 2
Actions: Relocated bulk pallet processing out of the main picking zone starting February 1 and used the freed capacity for order fulfillment recovery.
Priority Express Orders Impact: Express order backlog is fully cleared by the May 1 checkpoint.
Standard Freight Orders Impact: Standard freight backlog is reduced significantly, but a remainder is still open at May 1.
Bulk Pallet Loads Impact: Bulk pallet output in this zone is front-loaded before relocation, then remains zero in this zone after February 1.
May PO On-Time: Express Yes, Standard No

## Scenario 3
Actions: Relocated bulk pallets for the full horizon and ran a temporary 10-hour shift window after the required 30-day notification.
Priority Express Orders Impact: Express order demand is fully caught up by May 1.
Standard Freight Orders Impact: Standard freight demand is fully caught up by May 1.
Bulk Pallet Loads Impact: No bulk pallet processing is scheduled in the main picking zone, maximizing fulfillment throughput.
May PO On-Time: Yes
EOF

echo "Done."
