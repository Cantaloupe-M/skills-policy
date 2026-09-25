Complete the project proposal document `project_proposal_template.hwpx` using the values in `project_proposal.json`, then save the result to `/root/project_proposal_ready.hwpx`.

Requirements:
- Replace every `{{...}}` placeholder with the matching value from the JSON file across both sections.
- In addition to filling placeholders, append a parenthesized month span after each phase line using the corresponding date range already written in that line: `단계1` -> `(3개월)`, `단계2` -> `(3개월)`, `단계3` -> `(1개월)`.
- Normalize the budget value to remove commas before writing it into the document, while keeping the leading currency symbol.
- Keep all Korean labels and the static note line unchanged.
- No `{{...}}` placeholder text may remain anywhere in the output.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
