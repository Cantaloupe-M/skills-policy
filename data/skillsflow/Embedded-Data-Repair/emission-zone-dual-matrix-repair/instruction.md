You are repairing `/root/input.pptx`, an environmental compliance slide with an embedded Excel workbook that contains both archived and approved adjustment matrices on the same worksheet.

The slide note contains a draft factor line and a final approved factor line using short region codes. Use `/root/label_aliases.csv` to map the note codes to the workbook labels, use `/root/live_matrix_locator.json` to identify the approved matrix block, update only that matrix block, preserve formula cells as formulas, and save the corrected presentation to `/root/results.pptx`.

Requirements:
- Ignore any note marked draft or archived.
- Use `/root/label_aliases.csv` to resolve the note codes to workbook labels.
- Use `/root/live_matrix_locator.json` to identify the approved matrix block on the worksheet.
- Keep formula cells as formulas; do not replace them with hardcoded numbers.
- Let the reciprocal factor update through the workbook logic.
- Leave the archived matrix block, all other workbook values, and the rest of the presentation unchanged.
- Write the final file exactly to `/root/results.pptx`.
