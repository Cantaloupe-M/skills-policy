You are updating `/root/input.pptx`, a treasury review slide with an embedded Excel spot-rate grid.

Note: PowerPoint files are structured as ZIP archives containing XML markup. Some text operations may be easier by accessing the underlying XML directly.

The slide note contains one final cross-rate correction. Read that note, update the embedded workbook, preserve formula cells as formulas, and save the updated presentation to `/root/results.pptx`.

Requirements:
- Only change the live embedded Excel workbook inside the PPTX.
- Keep formula cells as formulas; do not replace them with hardcoded numbers.
- Let the reciprocal rate update through the workbook logic.
- Leave all other workbook values and presentation contents unchanged.
- Write the final file exactly to `/root/results.pptx`.
