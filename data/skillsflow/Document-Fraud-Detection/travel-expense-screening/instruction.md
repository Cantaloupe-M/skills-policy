You are helping a finance operations team review travel reimbursement claims.

Analyze these files:
- `/root/expense_claims.pdf`: one travel claim per page
- `/root/employee_directory.xlsx`: approved employees with `employee_id`, `employee_name`, `department_code`, and `bank_account`
- `/root/trip_approvals.csv`: approved trips with `trip_id`, `approved_amount`, and `employee_id`

A claim is suspicious if it meets ANY of the following criteria:
- Unknown Employee: the employee name does not match any employee in `employee_directory.xlsx`. Minor typos or small formatting variations can appear in the PDF names.
- Account Mismatch: the employee exists, but the bank account on the PDF does not match the employee's bank account.
- Invalid Trip ID: the trip ID is missing from the approvals file.
- Amount Mismatch: the trip exists, but the claimed amount differs from the approved amount by more than `0.01`.
- Traveler Mismatch: the trip exists, but it belongs to a different `employee_id` than the matched employee.

Write only the flagged claims to `/root/expense_alerts.json`.

Requirements:
- Use 1-based page indexing.
- Sort the JSON array by `claim_page_number` ascending.
- Copy `employee_name` and `bank_account` exactly as they appear on the PDF.
- If a page has no `Trip ID` line, set `trip_id` to `null`. Otherwise copy the Trip ID string exactly as shown, even if it later proves invalid.
- `reason` must be one of: `Unknown Employee`, `Account Mismatch`, `Invalid Trip ID`, `Amount Mismatch`, `Traveler Mismatch`.
- If multiple reasons apply, use the first reason in the order listed above.

Required JSON structure:
```json
[
  {
    "claim_page_number": 2,
    "employee_name": "Brian Ortega",
    "claimed_amount": 980.0,
    "bank_account": "WRONG-222",
    "trip_id": "TRIP-4102",
    "reason": "Account Mismatch"
  }
]
```
