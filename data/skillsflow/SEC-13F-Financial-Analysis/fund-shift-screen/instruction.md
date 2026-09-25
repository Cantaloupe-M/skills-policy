Prepare `/root/answers.json` by comparing one manager's stock holdings between `/root/2025-q2` and `/root/2025-q3`.

Use the manager name query `bridgewater associates` in each quarter separately. For each quarter, match the closest filing manager name in that quarter's cover page data, then use the accession number from that quarter.

Return a JSON object with exactly this schema:

```json
{
  "fund_query_current": "bridgewater associates",
  "quarter_current": "2025-q3",
  "fund_query_baseline": "bridgewater associates",
  "quarter_baseline": "2025-q2",
  "top4_increased_cusips": ["", "", "", ""],
  "top3_decreased_cusips": ["", "", ""],
  "new_positions_top2": ["", ""]
}
```

Requirements:
- Compare stock-like holdings only.
- Aggregate by CUSIP within each quarter before comparing.
- `top4_increased_cusips` must contain the 4 CUSIPs with the largest positive VALUE change from Q2 to Q3, ordered from largest increase to smaller increase.
- `top3_decreased_cusips` must contain the 3 CUSIPs with the most negative VALUE change, ordered from largest decrease to smaller decrease.
- `new_positions_top2` must contain the first 2 CUSIPs that were absent in Q2 and present in Q3, ordered by descending positive VALUE change.
- Use the quarter labels exactly as shown.
- Write only the JSON file requested.