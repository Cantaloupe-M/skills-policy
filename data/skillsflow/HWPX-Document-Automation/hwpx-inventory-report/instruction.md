Complete the inventory status report `inventory_report_template.hwpx` using the values in `inventory_data.json`, then save the result to `/root/inventory_report_ready.hwpx`.

Requirements:
- Replace every `{{...}}` placeholder with the matching value from the JSON file.
- Keep all Korean labels and the static note line unchanged.
- Preserve empty paragraphs (spacing) in the document structure.
- No `{{...}}` placeholder text may remain anywhere in the output.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
