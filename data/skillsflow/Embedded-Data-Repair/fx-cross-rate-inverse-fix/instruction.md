You are fixing `/root/input.pptx`, an investor board slide with an embedded Excel FX matrix.

Note: PowerPoint files are structured as ZIP archives containing XML markup. Some text operations may be easier by accessing the underlying XML directly.

The slide note contains one final cross-rate correction. Read that note, update the embedded workbook, preserve formula cells as formulas, and save the corrected presentation to `/root/results.pptx`.

Requirements:
- Only change the live embedded Excel workbook inside the PPTX.
- Keep formula cells as formulas; do not replace them with hardcoded numbers.
- If the noted direction is formula-driven in the workbook, update the corresponding writable input cell so the reciprocal still recalculates correctly.
- Leave all other workbook values and presentation contents unchanged.
- Write the final file exactly to `/root/results.pptx`.
