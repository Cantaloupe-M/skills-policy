You are the Fare Programs Analyst at MetroLink Transit Authority.

            Build an Excel workbook at:
            - `/root/MetroLink_Pass_Liability_4-25.xlsx`

            Use these normalized input files:
            - `/root/bus_pass_schedule_input.csv`
            - `/root/rail_pass_schedule_input.csv`
            - `/root/fare_liability_balances.json`

            For operational context only, source documents are also present:
            - `/root/MetroLink_Bus_Pass_Issuance_Notes_Q1Q2_2025.txt`
- `/root/MetroLink_Rail_Pass_Issuance_Notes_Q1Q2_2025.txt`
- `/root/metrolink_fare_ledger_control_notes_apr25.txt`

            Create exactly three sheets in this order:
            1. `Transit Summary`
            2. `Bus Program #4310`
            3. `Rail Program #4320`

            Keep the same row/column structure, control rows, and formula rules as the reference Harbor reconciliation task:
            - line items start at row 6
            - control rows: `Month Totals`, `Ending Balance`, `Variance`, `GL Balance`
            - summary formulas in B7/B8/B9/B12/B13/B14/B16 link to column O of the two detail tabs
            - B16 must be `B9+B14`

            Important:
            - Keep numeric values numeric (not text).
            - Do not change source files.
            - Final deliverable must be one `.xlsx` workbook at the required path.
