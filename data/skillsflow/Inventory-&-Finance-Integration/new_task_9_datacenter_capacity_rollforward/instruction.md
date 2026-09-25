You are the Cloud Capacity Operations Lead at Nimbus Compute.

            Build an Excel workbook at:
            - `/root/Nimbus_Capacity_Reconciliation_4-25.xlsx`

            Use these normalized input files:
            - `/root/compute_capacity_schedule_input.csv`
            - `/root/storage_capacity_schedule_input.csv`
            - `/root/capacity_ledger_balances.json`

            For operational context only, source documents are also present:
            - `/root/Nimbus_Compute_Reservation_Register_Q1Q2_2025.txt`
- `/root/Nimbus_Storage_Commitment_Register_Q1Q2_2025.txt`
- `/root/nimbus_platform_ledger_notes_apr25.txt`

            Create exactly three sheets in this order:
            1. `Capacity Summary`
            2. `Compute Pool #8100`
            3. `Storage Pool #8200`

            Keep the same row/column structure, control rows, and formula rules as the reference Harbor reconciliation task:
            - line items start at row 6
            - control rows: `Month Totals`, `Ending Balance`, `Variance`, `GL Balance`
            - summary formulas in B7/B8/B9/B12/B13/B14/B16 link to column O of the two detail tabs
            - B16 must be `B9+B14`

            Important:
            - Keep numeric values numeric (not text).
            - Do not change source files.
            - Final deliverable must be one `.xlsx` workbook at the required path.
