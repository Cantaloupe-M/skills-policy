You are auditing field service billing packets before payment.

Analyze these files:
- `/root/service_packets.pdf`: one billing packet per page
- `/root/contractor_directory.xlsx`: contractor records plus known name variants
- `/root/work_orders.csv`: base work orders
- `/root/work_order_revisions.csv`: optional work order revisions

Use these rules:
- Match contractor names against the contractor workbook, including known name variants. Minor typos or small formatting variations can appear in the PDF names.
- In `work_orders.csv`, only rows with `status = active` are valid base work orders.
- If `work_order_revisions.csv` contains one or more rows for the same `work_order_id` with `approval_state = approved`, keep the row with the highest `revision` and use its `revised_amount` as the expected amount.

A packet is suspicious if it meets ANY of the following criteria:
- Unknown Contractor: the contractor name does not resolve to any contractor in the workbook.
- Account Mismatch: the contractor exists, but the payment account on the PDF does not match the contractor record.
- Invalid Work Order: the work order is missing from the valid base orders.
- Amount Mismatch: the work order exists, but the billed amount differs from the expected amount by more than `0.01` after applying the revision rule above.
- Contractor Mismatch: the work order exists, but it belongs to a different `contractor_id` than the matched contractor.

Write only the flagged packets to `/root/service_audit_flags.json`.

Requirements:
- Use 1-based page indexing.
- Sort the JSON array by `packet_page_number` ascending.
- Copy `contractor_name` and `payment_account` exactly as they appear on the PDF.
- If a page has no `Work Order` line, set `work_order_id` to `null`. Otherwise copy the work order ID exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Contractor`, `Account Mismatch`, `Invalid Work Order`, `Amount Mismatch`, `Contractor Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "packet_page_number": 4,
    "contractor_name": "Harbor Electric LLC",
    "billed_amount": 2750.0,
    "payment_account": "ACC-HE-4",
    "work_order_id": "WO-8806",
    "reason": "Invalid Work Order"
  }
]
```
