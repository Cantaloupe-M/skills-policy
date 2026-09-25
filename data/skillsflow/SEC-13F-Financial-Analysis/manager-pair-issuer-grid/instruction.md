Create `/root/answers.json` from the filing data in `/root/2025-q3`.

Build a manager-versus-issuer grid for two manager queries and two issuer queries.

Return a JSON object with exactly this shape:

```json
{
  "manager_issuer_grid": [
    {
      "fund_query": "bridgewater associates",
      "quarter": "2025-q3",
      "issuer_queries": [
        {"issuer_query": "amazon", "cusip": "", "value": 0},
        {"issuer_query": "palantir", "cusip": "", "value": 0}
      ]
    },
    {
      "fund_query": "third point",
      "quarter": "2025-q3",
      "issuer_queries": [
        {"issuer_query": "amazon", "cusip": "", "value": 0},
        {"issuer_query": "palantir", "cusip": "", "value": 0}
      ]
    }
  ]
}
```

Requirements:
- Resolve each manager query against the Q3 cover page data.
- Resolve each issuer query to one stock CUSIP.
- For each manager and issuer pair, sum VALUE across all Q3 rows in that filing for the resolved CUSIP.
- Keep the manager order and issuer order exactly as shown.
- Use numeric values, not strings.
- Write only the JSON file requested.