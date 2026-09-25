Update the existing JSON report at `/root/brief_template.json` and save the completed result as `/root/answers.json`.

Use the filing data in `/root/2025-q2` and `/root/2025-q3` to fill in the placeholder values while preserving the existing structure and any untouched content.

The final JSON must keep the same top-level keys, section order, item order, and notes array as the template.

Fill the report as follows:
- Set `report_date` to `2025-q3`.
- In section `fund_snapshots`, for `renaissance technologies` and `scion asset management`, resolve each manager in Q3 and fill `aum` with total VALUE across the filing and `stock_holdings` with the count of stock-like rows.
- In section `issuer_leaders`, for `palantir` and `meta platforms`, resolve each issuer to one stock CUSIP and fill `top_manager` with the Q3 manager name having the highest aggregated VALUE for that CUSIP.
- In section `change_checks`, for `bridgewater associates` and `third point`, resolve each manager separately in Q2 and Q3, compare stock-like holdings by CUSIP, and fill `largest_buy_cusip` and `largest_sell_cusip`.
- Preserve the existing `notes` content exactly.

Write only the completed JSON report to `/root/answers.json`.