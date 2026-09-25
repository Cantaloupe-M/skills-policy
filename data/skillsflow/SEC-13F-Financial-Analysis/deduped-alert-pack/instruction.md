Use the filing data in `/root/2025-q2` and `/root/2025-q3` together with `/root/alerts_input.json` to create `/root/answers.json`.

`alerts_input.json` contains a mixed alert feed. Some entries are duplicates, and some entries are distractors that must be ignored.

Produce a JSON object with exactly these top-level keys:

```json
{
  "issuer_top_holders": [
    {
      "issuer_query": "",
      "quarter": "",
      "manager_names": ["", "", ""]
    }
  ],
  "fund_change": [
    {
      "fund_query_current": "",
      "quarter_current": "",
      "fund_query_baseline": "",
      "quarter_baseline": "",
      "largest_buy_cusip": ""
    }
  ]
}
```

Requirements:
- Process only alert objects whose `type` is `issuer_top_holders` or `fund_change`.
- Ignore every other alert type.
- Deduplicate alerts within each type by their semantic content, not by object position.
- Preserve the first-seen order of distinct alerts within each type.
- For `issuer_top_holders`, resolve the issuer query to one stock CUSIP, then return the top 3 Q3 manager names by aggregated VALUE for that CUSIP.
- For `fund_change`, resolve the fund query separately in Q2 and Q3, compare stock-like holdings only, and return the single CUSIP with the largest positive VALUE change.
- Write only the JSON file requested.