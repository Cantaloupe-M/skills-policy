You are correcting `/root/input.pptx`, a process engineering slide with an embedded Excel catalyst-balance workbook.

The slide note gives one final ratio update using short catalyst codes. Use `/root/label_aliases.csv` to match those codes to the workbook labels, update the live catalyst matrix in the embedded workbook, preserve formula cells as formulas, and save the corrected presentation to `/root/results.pptx`.

Requirements:
- Only the live catalyst matrix sheet should change.
- Use `/root/label_aliases.csv` to resolve the note codes to workbook labels.
- Keep formula cells as formulas; do not replace them with hardcoded numbers.
- Let the reciprocal ratio update through the workbook logic.
- Leave the cover sheet, all other workbook values, and the rest of the presentation unchanged.
- Write the final file exactly to `/root/results.pptx`.
