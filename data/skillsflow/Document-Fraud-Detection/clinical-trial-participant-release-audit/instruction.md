You are reconciling participant release requests for a clinical trials payment team.

Analyze these files:
- `/root/participant_release_bundle.pdf`: request pages plus cover or resubmission pages
- `/root/participant_registry.xlsx`: `participants` sheet with approved participants and `aliases` sheet with known name variants
- `/root/award_catalog.json`: award entries grouped under sponsor and program containers
- `/root/release_versions.csv`: optional award version overrides

Use these rules:
- Only pages whose first non-empty line is exactly `Participant Release Request` are in scope. Ignore all other pages completely.
- Each in-scope page contains `Packet Ref` and `Revision No`.
- If multiple in-scope pages share the same `Packet Ref`, evaluate only the page with the highest `Revision No`. If the same `Packet Ref` and `Revision No` appears more than once, keep only the later page in the PDF.
- Match participant names against the workbook, including known aliases. Minor typos or small formatting variations can appear in the PDF names.
- Flatten all award entries under every sponsor and program container in `award_catalog.json`.
- Use only flattened award entries where `status` is `active`.
- In `release_versions.csv`, use only rows where `approval_state` is `approved` and both `version_amount` and `participant_code` are non-empty.
- If multiple usable version rows exist for the same `award_ref`, keep the row with the highest `version_no` and use both its `version_amount` and `participant_code`.

A retained request page is suspicious if it meets ANY of the following criteria:
- Unknown Participant: the participant name does not resolve to any participant in the workbook.
- Account Mismatch: the participant exists, but the payment token on the PDF does not match the participant record.
- Invalid Award Ref: the award reference is missing from the valid flattened award set.
- Amount Mismatch: the award exists, but the requested amount differs from the expected amount by more than `0.01` after applying the version rule above.
- Participant Mismatch: the award exists, but it belongs to a different `participant_code` than the matched participant after applying the version rule above.

Write only the flagged retained request pages to `/root/participant_release_flags.json`.

Requirements:
- Use the original 1-based PDF page numbers of the retained request pages.
- Sort the JSON array by `request_page_number` ascending.
- Copy `participant_name` and `payment_token` exactly as they appear on the PDF.
- If a retained request page has no `Award Ref` line, set `award_ref` to `null`. Otherwise copy the award reference exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Participant`, `Account Mismatch`, `Invalid Award Ref`, `Amount Mismatch`, `Participant Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "request_page_number": 9,
    "participant_name": "Dana Holt",
    "requested_amount": 1050.0,
    "payment_token": "PT-1004",
    "award_ref": "AR-5004",
    "reason": "Amount Mismatch"
  }
]
```
