You are reviewing overnight clinic shift payment claims.

Analyze these files:
- `/root/shift_claims.pdf`: one claim per page
- `/root/clinician_directory.xlsx`: approved clinicians with `clinician_id`, `clinician_name`, `unit_code`, and `payout_account`
- `/root/shift_authorizations.csv`: valid shift authorizations with `shift_code_internal`, `approved_pay`, and `clinician_id`
- `/root/shift_crosswalk.csv`: mapping from PDF `shift_ref` values to `shift_code_internal`

A claim is suspicious if it meets ANY of the following criteria:
- Unknown Clinician: the clinician name does not match any clinician in the workbook. Minor typos or small formatting variations can appear in the PDF names.
- Account Mismatch: the clinician exists, but the payout account on the PDF does not match the clinician record.
- Invalid Shift Code: the PDF `shift_ref` is missing from `shift_crosswalk.csv`, or its mapped `shift_code_internal` is missing from `shift_authorizations.csv`.
- Amount Mismatch: the shift exists, but the requested pay differs from the approved pay by more than `0.01`.
- Clinician Mismatch: the shift exists, but it belongs to a different `clinician_id` than the matched clinician.

Write only the flagged claims to `/root/shift_claim_flags.json`.

Requirements:
- Use 1-based page indexing.
- Sort the JSON array by `claim_page_number` ascending.
- Copy `clinician_name` and `payout_account` exactly as they appear on the PDF.
- If a page has no `Shift Ref` line, set `shift_ref` to `null`. Otherwise copy the shift reference exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Clinician`, `Account Mismatch`, `Invalid Shift Code`, `Amount Mismatch`, `Clinician Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "claim_page_number": 4,
    "clinician_name": "Victor Han",
    "requested_pay": 520.0,
    "payout_account": "BAD-702",
    "shift_ref": "SHIFT-B2",
    "reason": "Account Mismatch"
  }
]
```
