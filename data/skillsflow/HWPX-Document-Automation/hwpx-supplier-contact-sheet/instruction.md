Update the HWPX supplier contact sheet `supplier_contact_template.hwpx` using the values in `supplier_contact.json`, then save the finished file to `/root/supplier_contact_ready.hwpx`.

Requirements:
- Replace every `{{...}}` placeholder with the matching value from the JSON file.
- Keep each Korean field label already in the document.
- Leave the static note line unchanged.
- No `{{...}}` placeholders may remain anywhere in the output.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
