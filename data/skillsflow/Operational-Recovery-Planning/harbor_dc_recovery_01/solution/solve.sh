#!/bin/bash
set -euo pipefail

python3 - << 'PY'
from openpyxl import load_workbook

source_path = "/solution/Server_Provisioning_Recovery_Plan_Analysis.xlsx"
output_path = "/root/server_provisioning_recovery_plan_analysis.xlsx"

wb = load_workbook(source_path)

for ws in wb.worksheets:
    if ws.max_row > 103:
        ws.delete_rows(104, ws.max_row - 103)

    ws["D4"] = 1065
    ws["G4"] = 855

    for row in range(4, 104):
        if ws.title == "10 hr Shift Relocate Network Eq":
            ws.cell(row=row, column=9).value = 0
        ws.cell(row=row, column=10).value = f"=C{row}+F{row}+I{row}"

wb.save(output_path)
print(f"Saved workbook to {output_path}")
PY

cat > /root/server_provisioning_recovery_summary.md << 'EOF'
## Scenario 1
Actions: Kept network appliance provisioning in the server rack bay while operating one 8-hour shift, then moved to the 135 units/day rate after the February 5 capacity step-up.
Rack-Mount Web Servers Impact: Web server backlog is reduced but May demand is still open at the end of the planning horizon.
Blade Database Servers Impact: Database server provisioning starts later and May database demand remains open by May 1.
Network Appliances Impact: Network appliance cadence is maintained in this bay, but it consumes capacity needed for server provisioning catch-up.
May PO On-Time: No

## Scenario 2
Actions: Relocated network appliance provisioning out of the server rack bay starting February 1 and used the freed capacity for server provisioning recovery.
Rack-Mount Web Servers Impact: Web server backlog is fully cleared by the May 1 checkpoint.
Blade Database Servers Impact: Database server backlog is reduced significantly, but a remainder is still open at May 1.
Network Appliances Impact: Network appliance output in this bay is front-loaded before relocation, then remains zero in this bay after February 1.
May PO On-Time: Web Yes, Database No

## Scenario 3
Actions: Relocated network appliances for the full horizon and ran a temporary 10-hour shift window after the required 30-day notification.
Rack-Mount Web Servers Impact: Web server demand is fully caught up by May 1.
Blade Database Servers Impact: Database server demand is fully caught up by May 1.
Network Appliances Impact: No network appliance provisioning is scheduled in the server rack bay, maximizing recovery throughput.
May PO On-Time: Yes
EOF

echo "Done."
