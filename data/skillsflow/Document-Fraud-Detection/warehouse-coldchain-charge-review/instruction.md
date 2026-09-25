You are reviewing cold-chain charge requests from a warehouse receiving team.

Analyze these files:
- `/root/coldchain_charge_packets.pdf`: request pages plus appendix pages
- `/root/carrier_registry.xlsx`: `carriers` sheet with approved carriers and `aliases` sheet with known name variants
- `/root/shipment_authorizations.csv`: base shipment authorizations
- `/root/shipment_snapshots.csv`: optional later shipment snapshots

Use these rules:
- Only pages whose first non-empty line is exactly `Cold Chain Charge Request` are in scope. Ignore all other pages completely.
- Match carrier names against the workbook, including known aliases. Minor typos or small formatting variations can appear in the PDF names.
- In `shipment_authorizations.csv`, use only rows where `record_state` is `approved`.
- In `shipment_snapshots.csv`, use only rows where `snapshot_state` is `approved` and both `expected_charge` and `carrier_id` are non-empty.
- If multiple usable snapshot rows exist for the same `shipment_ref`, keep the row with the highest `snapshot_seq` and use both its `expected_charge` and `carrier_id`.

A request is suspicious if it meets ANY of the following criteria:
- Unknown Carrier: the carrier name does not resolve to any carrier in the workbook.
- Account Mismatch: the carrier exists, but the remit account on the PDF does not match the carrier record.
- Invalid Shipment Ref: the shipment reference is missing from the valid shipment set.
- Amount Mismatch: the shipment exists, but the requested charge differs from the expected amount by more than `0.01` after applying the snapshot rule above.
- Carrier Mismatch: the shipment exists, but it belongs to a different `carrier_id` than the matched carrier after applying the snapshot rule above.

Write only the flagged in-scope requests to `/root/coldchain_charge_flags.json`.

Requirements:
- Use the original 1-based PDF page numbers.
- Sort the JSON array by `request_page_number` ascending.
- Copy `carrier_name` and `remit_account` exactly as they appear on the PDF.
- If an in-scope page has no `Shipment Ref` line, set `shipment_ref` to `null`. Otherwise copy the shipment reference exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Carrier`, `Account Mismatch`, `Invalid Shipment Ref`, `Amount Mismatch`, `Carrier Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "request_page_number": 6,
    "carrier_name": "Glacier Freight",
    "requested_charge": 915.0,
    "remit_account": "BAD-902",
    "shipment_ref": "SH-7102",
    "reason": "Account Mismatch"
  }
]
```
