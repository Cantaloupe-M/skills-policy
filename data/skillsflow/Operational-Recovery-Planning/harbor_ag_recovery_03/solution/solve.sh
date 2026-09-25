#!/bin/bash
set -euo pipefail

python3 - << 'PY'
from openpyxl import load_workbook

source_path = "/solution/Harvest_Recovery_Plan_Analysis.xlsx"
output_path = "/root/harvest_recovery_plan_analysis.xlsx"

wb = load_workbook(source_path)

for ws in wb.worksheets:
    if ws.max_row > 103:
        ws.delete_rows(104, ws.max_row - 103)

    ws["D4"] = 1065
    ws["G4"] = 855

    for row in range(4, 104):
        if ws.title == "10 hr Shift Relocate Flax Proc":
            ws.cell(row=row, column=9).value = 0
        ws.cell(row=row, column=10).value = f"=C{row}+F{row}+I{row}"

wb.save(output_path)
print(f"Saved workbook to {output_path}")
PY

cat > /root/harvest_recovery_summary.md << 'EOF'
## Scenario 1
Actions: Kept flax processing in the main harvest equipment line while operating one 8-hour shift, then moved to the 135 loads/day rate after the February 5 capacity step-up.
Wheat Bin Loads Impact: Wheat backlog is reduced but May demand is still open at the end of the planning horizon.
Canola Bin Loads Impact: Canola delivery starts later and May canola demand remains open by May 1.
Flax Processing Impact: Flax processing cadence is maintained on this line, but it consumes capacity needed for harvest delivery catch-up.
May PO On-Time: No

## Scenario 2
Actions: Relocated flax processing off the main harvest equipment line starting February 1 and used the freed capacity for harvest delivery recovery.
Wheat Bin Loads Impact: Wheat backlog is fully cleared by the May 1 checkpoint.
Canola Bin Loads Impact: Canola backlog is reduced significantly, but a remainder is still open at May 1.
Flax Processing Impact: Flax output on this line is front-loaded before relocation, then remains zero on this line after February 1.
May PO On-Time: Wheat Yes, Canola No

## Scenario 3
Actions: Relocated flax processing for the full horizon and ran a temporary 10-hour shift window after the required 30-day notification.
Wheat Bin Loads Impact: Wheat demand is fully caught up by May 1.
Canola Bin Loads Impact: Canola demand is fully caught up by May 1.
Flax Processing Impact: No flax processing is scheduled on the main harvest equipment line, maximizing harvest delivery throughput.
May PO On-Time: Yes
EOF

echo "Done."
