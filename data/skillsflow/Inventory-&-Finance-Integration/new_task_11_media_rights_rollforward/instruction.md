You are the Content Rights Operations Manager at Aurora Stream.

            Build an Excel workbook at:
            - `/root/Aurora_Rights_Rollforward_4-25.xlsx`

            Use these normalized input files:
            - `/root/film_rights_schedule_input.csv`
            - `/root/music_rights_schedule_input.csv`
            - `/root/rights_ledger_balances.json`

            For operational context only, source documents are also present:
            - `/root/Aurora_Film_Licensor_Invoices_Q1Q2_2025.txt`
- `/root/Aurora_Music_Licensor_Invoices_Q1Q2_2025.txt`
- `/root/aurora_rights_ledger_control_notes_apr25.txt`

            Create exactly three sheets in this order:
            1. `Rights Summary`
            2. `Film Rights #2710`
            3. `Music Rights #2720`

            Keep the same row/column structure, control rows, and formula rules as the reference Harbor reconciliation task:
            - line items start at row 6
            - control rows: `Month Totals`, `Ending Balance`, `Variance`, `GL Balance`
            - summary formulas in B7/B8/B9/B12/B13/B14/B16 link to column O of the two detail tabs
            - B16 must be `B9+B14`

            Important:
            - Keep numeric values numeric (not text).
            - Do not change source files.
            - Final deliverable must be one `.xlsx` workbook at the required path.
