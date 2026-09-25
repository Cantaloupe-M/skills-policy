#!/bin/bash
set -euo pipefail

python3 - << 'PY'
from openpyxl import load_workbook

source_path = "/solution/Running_Board_Recovery_Plan_Analysis.xlsx"
output_path = "/root/running_board_recovery_plan_analysis.xlsx"

wb = load_workbook(source_path)

for ws in wb.worksheets:
    # Keep only the required planning horizon through 2018-05-01 (rows 4..103).
    if ws.max_row > 103:
        ws.delete_rows(104, ws.max_row - 103)

    # Ensure PO due columns are numeric constants in required columns.
    ws["D4"] = 1065
    ws["G4"] = 855

    # Ensure Total Prod is formula-driven for the full required horizon.
    for row in range(4, 104):
        if ws.title == "10 hr Shift Relocate Grill Guar":
            ws.cell(row=row, column=9).value = 0
        ws.cell(row=row, column=10).value = f"=C{row}+F{row}+I{row}"

wb.save(output_path)
print(f"Saved workbook to {output_path}")
PY

cat > /root/running_board_recovery_summary.md << 'EOF'
## Scenario 1
Actions: Kept grill guard production in the running board cell while operating one 8-hour shift, then moved to the 135 sets/day rate after the February 5 capacity step-up.
Crew Cab Impact: Crew backlog is reduced but May demand is still open at the end of the planning horizon.
Extended Cab Impact: Extended production starts later and May extended demand remains open by May 1.
Grill Guard Impact: Grill guard cadence is maintained in this cell, but it consumes capacity needed for running board catch-up.
May PO On-Time: No

## Scenario 2
Actions: Relocated grill guard production out of the running board cell starting February 1 and used the freed capacity for running board recovery.
Crew Cab Impact: Crew backlog is fully cleared by the May 1 checkpoint.
Extended Cab Impact: Extended backlog is reduced significantly, but a remainder is still open at May 1.
Grill Guard Impact: Grill guard output in this cell is front-loaded before relocation, then remains zero in this cell after February 1.
May PO On-Time: Crew Yes, Extended No

## Scenario 3
Actions: Relocated grill guard for the full horizon and ran a temporary 10-hour shift window after the required 30-day notification.
Crew Cab Impact: Crew demand is fully caught up by May 1.
Extended Cab Impact: Extended demand is fully caught up by May 1.
Grill Guard Impact: No grill guard production is scheduled in the running board cell, maximizing recovery throughput.
May PO On-Time: Yes
EOF

echo "Done."
