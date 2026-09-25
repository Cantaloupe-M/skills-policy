Fill in the training feedback sheet `training_feedback_template.hwpx` using the values in `training_feedback.json`, then save the result to `/root/training_feedback_ready.hwpx`.

Requirements:
- Replace every `{{...}}` placeholder with the matching value from the JSON file across both sections.
- Convert `참석자수` into digits only before writing it.
- Rewrite `만족도` as `4.5점 (5.0점 만점)` style, preserving the numeric score from the JSON.
- In the final overall-opinion sentence, append `후속 심화반 검토 요망.` after the provided comment.
- Keep all Korean labels and the static note line unchanged.
- No `{{...}}` placeholder text may remain anywhere in the output.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
