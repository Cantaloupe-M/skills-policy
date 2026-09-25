Revise the existing renewal playbook `renewal_playbook.hwpx` using `renewal_update.json` and `followups.csv`, then save the updated file to `/root/renewal_playbook_updated.hwpx`.

Requirements:
- Update the customer name, current owner, renewal window, pricing band, escalation contact, and pricing note everywhere they appear in the editable sections.
- Replace the three follow-up lines with the CSV items in `sequence` order.
- Remove the old values rather than adding duplicate lines beside them.
- Keep the appendix sentence `이 부록 문단은 그대로 유지해야 합니다.` unchanged.
- The result must remain a valid `.hwpx` package.
- Any paragraph whose text you modify must not retain stale layout-cache elements, so the edited document can open cleanly without overlapping characters.
