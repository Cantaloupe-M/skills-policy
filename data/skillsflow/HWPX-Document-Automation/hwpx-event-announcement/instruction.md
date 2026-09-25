Prepare the event announcement document `event_announcement_template.hwpx` using the values in `event_data.json`, then save the result to `/root/event_announcement_ready.hwpx`.

Requirements:
- Replace every `{{...}}` placeholder with the matching value from the JSON file.
- Keep all Korean labels and the static note line unchanged.
- No `{{...}}` placeholder text may remain anywhere in the output.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
