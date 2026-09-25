You are reconciling research stipend disbursement packets.

Analyze these files:
- `/root/stipend_packets.pdf`: a packet PDF that may include cover or appendix pages
- `/root/recipient_roster.xlsx`: recipient records plus known name variants
- `/root/award_authorizations.csv`: base award authorizations
- `/root/award_adjustments.csv`: optional award adjustments

Use these rules:
- Only pages whose first line is exactly `Stipend Disbursement Request` are in scope. Ignore all other pages completely.
- Match recipient names against the roster workbook, including known name variants. Minor typos or small formatting variations can appear in the PDF names.
- In `award_authorizations.csv`, only rows with `state = active` are valid base awards.
- If `award_adjustments.csv` contains one or more rows for the same `award_ref` with `state = approved`, keep the row with the highest `revision_no` and use its `adjusted_value` and `campus_code`.

A request is suspicious if it meets ANY of the following criteria:
- Unknown Recipient: the recipient name does not resolve to any recipient in the workbook.
- Account Mismatch: the recipient exists, but the bank token on the PDF does not match the roster.
- Invalid Award Ref: the award reference is missing from the valid base authorizations.
- Amount Mismatch: the award exists, but the requested amount differs from the expected amount by more than `0.01` after applying the adjustment rule above.
- Campus Mismatch: the award exists, but the campus on the PDF does not match the expected campus after applying the adjustment rule above.

Write only the flagged in-scope requests to `/root/stipend_review.json`.

Requirements:
- Use the original 1-based PDF page numbers.
- Sort the JSON array by `request_page_number` ascending.
- Copy `recipient_name` and `bank_token` exactly as they appear on the PDF.
- If an in-scope page has no `Award Ref` line, set `award_ref` to `null`. Otherwise copy the award reference exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Recipient`, `Account Mismatch`, `Invalid Award Ref`, `Amount Mismatch`, `Campus Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "request_page_number": 7,
    "recipient_name": "Leah Brooks",
    "requested_amount": 2100.0,
    "bank_token": "BANK-505",
    "award_ref": "AWD-3005",
    "reason": "Invalid Award Ref"
  }
]
```
