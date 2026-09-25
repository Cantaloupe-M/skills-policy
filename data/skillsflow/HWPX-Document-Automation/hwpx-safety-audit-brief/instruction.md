Prepare the warehouse safety audit brief `safety_audit_template.hwpx` using both `audit_overview.json` and `corrective_actions.json`, then save it to `/root/safety_audit_brief_final.hwpx`.

Requirements:
- Fill the overview fields in the summary section and the value cells in the audit table.
- Fill the three corrective-action lines in the same order they appear in `corrective_actions.json`.
- Update every occurrence of the risk tier.
- Rewrite the inspection date from `YYYY-MM-DD` to `YYYY.MM.DD` everywhere it appears.
- Add a short severity note immediately after the risk tier using this mapping: `High -> 즉시조치`, `Medium -> 계획보완`, `Low -> 모니터링`.
- Keep the existing section titles and row labels.
- Do not leave any `{{...}}` placeholder text anywhere in either section.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
