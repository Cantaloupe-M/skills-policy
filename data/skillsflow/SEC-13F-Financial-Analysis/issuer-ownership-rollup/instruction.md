Create `/root/answers.json` for an issuer ownership rollup using the 13F data in `/root/2025-q2` and `/root/2025-q3`.

Use the issuer name query `palantir` to identify the correct stock CUSIP. Match the closest issuer name from the available stock rows, then use that CUSIP against the Q3 holdings data.

Return a JSON object with exactly this schema:

```json
{
  "issuer_query": "palantir",
  "quarter": "2025-q3",
  "cusip": "",
  "top5_managers": ["", "", "", "", ""],
  "top5_accessions": ["", "", "", "", ""]
}
```

Requirements:
- Resolve the issuer query to one CUSIP first.
- In Q3, aggregate VALUE by ACCESSION_NUMBER for that CUSIP.
- Rank managers by descending aggregated VALUE for that CUSIP.
- `top5_managers` and `top5_accessions` must refer to the same ranked rows in the same order.
- Manager names must come from the Q3 cover page data.
- Write only the JSON file requested.