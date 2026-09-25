You are reviewing speaker honorarium requests for an events team.

Analyze these files:
- `/root/honorarium_requests.pdf`: one request per page
- `/root/speaker_registry.xlsx`: approved speakers with `speaker_id`, `speaker_name`, `organization_code`, and `payment_account`
- `/root/session_approvals.csv`: approved sessions with `approval_code`, `approved_fee`, and `speaker_id`

A request is suspicious if it meets ANY of the following criteria:
- Unknown Speaker: the speaker name does not match any approved speaker. Minor typos or small formatting variations can appear in the PDF names.
- Account Mismatch: the speaker exists, but the payment account on the PDF does not match the registry.
- Invalid Approval Code: the approval code is missing from the approvals file.
- Fee Mismatch: the approval exists, but the requested fee differs from the approved fee by more than `0.01`.
- Speaker Mismatch: the approval exists, but it belongs to a different `speaker_id` than the matched speaker.

Write only the flagged requests to `/root/honorarium_flags.json`.

Requirements:
- Use 1-based page indexing.
- Sort the JSON array by `request_page_number` ascending.
- Copy `speaker_name` and `payment_account` exactly as they appear on the PDF.
- If a page has no `Approval Code` line, set `approval_code` to `null`. Otherwise copy the approval code exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Speaker`, `Account Mismatch`, `Invalid Approval Code`, `Fee Mismatch`, `Speaker Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "request_page_number": 6,
    "speaker_name": "Marisa Cole",
    "requested_fee": 900.0,
    "payment_account": "PAY-88",
    "approval_code": "AP-7004",
    "reason": "Unknown Speaker"
  }
]
```
