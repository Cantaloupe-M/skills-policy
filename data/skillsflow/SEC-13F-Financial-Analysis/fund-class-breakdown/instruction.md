Create `/root/answers.json` using the Q3 filing data in `/root/2025-q3`.

Use the manager name query `elliott associates` to resolve the correct filing manager in the Q3 cover page data. Then compute a class breakdown for that filing.

Return a JSON object with exactly this schema:

```json
{
  "fund_query": "elliott associates",
  "quarter": "2025-q3",
  "aum_total": 0,
  "stock_row_count": 0,
  "stock_cusip_count": 0,
  "top_class_labels": ["", "", "", ""],
  "top_class_counts": [0, 0, 0, 0]
}
```

Requirements:
- `aum_total` is the total VALUE across all rows in the matched filing.
- Treat stock-like rows the same way throughout the task family.
- `stock_row_count` is the number of stock-like rows in the filing.
- `stock_cusip_count` is the number of distinct stock CUSIPs after grouping those stock-like rows by CUSIP.
- `top_class_labels` and `top_class_counts` must describe the 4 most frequent normalized stock-like `TITLEOFCLASS` labels within the filing.
- Normalize `TITLEOFCLASS` by lowercasing before counting.
- Order the class breakdown by descending count, breaking ties by ascending normalized label.
- Write only the JSON file requested.