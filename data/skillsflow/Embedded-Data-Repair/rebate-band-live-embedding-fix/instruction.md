You are fixing `/root/input.pptx`, a channel rebate slide whose PPTX package contains two embedded Excel workbooks: one live and one archived.

The slide note includes an archived rebate line and a current approved rebate line. Use `/root/live_embedding.json` to identify which embedded workbook is live, update only that workbook, preserve formula cells as formulas, and save the corrected presentation to `/root/results.pptx`.

Requirements:
- Read `/root/live_embedding.json` to identify the live embedded workbook.
- Ignore any note marked archived.
- Keep formula cells as formulas; do not replace them with hardcoded numbers.
- Let the reciprocal uplift update through the workbook logic.
- Leave the archived embedded workbook, all other workbook values, and the rest of the presentation unchanged.
- Write the final file exactly to `/root/results.pptx`.
