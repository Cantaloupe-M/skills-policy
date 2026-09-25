You are auditing fleet maintenance chargeback packets before payment.

Analyze these files:
- `/root/chargeback_packets.pdf`: one chargeback packet per page
- `/root/provider_directory.xlsx`: `providers` sheet with approved providers and `aliases` sheet with known name variants
- `/root/maintenance_orders.json`: maintenance orders grouped by depot
- `/root/maintenance_adjustments.csv`: optional charge amendments

Use these rules:
- Match provider names against the workbook, including known aliases. Minor typos or small formatting variations can appear in the PDF names.
- Flatten all orders under all depots in `maintenance_orders.json`.
- Use only order entries where `lifecycle` is `approved`.
- If `maintenance_adjustments.csv` contains one or more rows for the same `order_id` with `decision = approved`, keep the row with the highest `amendment_no` and use its `amended_charge` as the expected amount.

A packet is suspicious if it meets ANY of the following criteria:
- Unknown Provider: the provider name does not resolve to any provider in the workbook.
- Account Mismatch: the provider exists, but the payment account on the PDF does not match the provider record.
- Invalid Order ID: the order ID is missing from the valid flattened order set.
- Amount Mismatch: the order exists, but the chargeback total differs from the expected amount by more than `0.01` after applying the amendment rule above.
- Provider Mismatch: the order exists, but it belongs to a different `provider_id` than the matched provider.

Write only the flagged packets to `/root/fleet_chargeback_flags.json`.

Requirements:
- Use 1-based page indexing.
- Sort the JSON array by `packet_page_number` ascending.
- Copy `provider_name` and `payment_account` exactly as they appear on the PDF.
- If a page has no `Order ID` line, set `order_id` to `null`. Otherwise copy the order ID exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Provider`, `Account Mismatch`, `Invalid Order ID`, `Amount Mismatch`, `Provider Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "packet_page_number": 5,
    "provider_name": "Beacon Tire Co",
    "chargeback_total": 980.0,
    "payment_account": "ACC-804",
    "order_id": "MO-9999",
    "reason": "Invalid Order ID"
  }
]
```
