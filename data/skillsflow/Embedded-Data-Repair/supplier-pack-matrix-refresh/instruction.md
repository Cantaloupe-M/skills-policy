You are fixing `/root/input.pptx`, a procurement slide with an embedded Excel packaging-conversion workbook.

The slide note includes one archived conversion and one final live correction. Update only the live pack matrix in the embedded workbook, ignore any note marked archived, preserve formula cells as formulas, and save the corrected presentation to `/root/results.pptx`.

Requirements:
- The embedded workbook has more than one sheet; only the live pack matrix sheet should change.
- Keep formula cells as formulas; do not replace them with hardcoded numbers.
- Let the reciprocal conversion update through the workbook logic.
- Leave all other workbook values, other sheets, and presentation contents unchanged.
- Write the final file exactly to `/root/results.pptx`.
