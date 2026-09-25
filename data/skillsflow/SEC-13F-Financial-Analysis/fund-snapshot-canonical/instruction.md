Review the Q3 2025 filing data in `/root/2025-q3` and prepare a single JSON file at `/root/answers.json`.

Use the filing manager name query `renaissance technologies` to identify the correct fund. Match the manager name using the following normalization steps:

1. **Normalize both query and candidate names**:
   - Convert to lowercase
   - Remove all punctuation (commas, periods, hyphens, etc.)
   - Remove common company suffixes: `llc`, `lp`, `ltd`, `inc`, `corp`, `corporation`, `company`, `co`, `partners`, `management`, `advisors`, `capital`, `group`, `holdings` (only remove if they appear as standalone words at the end)
   - Collapse multiple spaces to single space
   - Strip leading/trailing whitespace

2. **Match candidates**:
   - If there's an exact match after normalization, use that filing
   - If no exact match, choose the candidate with the shortest Levenshtein distance (edit distance) to the normalized query
   - If multiple candidates have the same minimum distance, choose the one that appears first alphabetically

3. **Use the matched filing**:
   - Once you've identified the correct manager, use that filing's accession number for all subsequent data extraction

**Stock-like class definition**: A row is considered stock-like if its `TITLEOFCLASS` field contains any of these case-insensitive substrings:
- `stock` (e.g., "Common Stock", "Ordinary Shares")
- `share` (e.g., "Class A Shares")
- `ordinary` (e.g., "Ordinary Shares")
- `common` (e.g., "Common Stock")

But **exclude** if it contains:
- `preferred` (e.g., "Preferred Stock")
- `option` (e.g., "Stock Options")
- `warrant` (e.g., "Warrants")
- `right` (e.g., "Rights")
- `debt` or `note` or `bond` (e.g., "Corporate Bond")
- `put` or `call` (e.g., "Put Option")

Return a JSON object with exactly these keys:

```json
{
  "fund_query": "renaissance technologies",
  "quarter": "2025-q3",
  "matched_manager": "",
  "accession_number": "",
  "aum": 0,
  "stock_holdings": 0,
  "stock_aum": 0,
  "top3_cusips_by_value": ["", "", ""]
}
```

Requirements:
- `matched_manager` must be the exact manager name from COVERPAGE.tsv (not normalized)
- `accession_number` must be the ACCESSION_NUMBER from COVERPAGE.tsv for the matched manager
- `aum` must be the total VALUE across all holdings for the matched filing.
- `stock_holdings` must count only rows whose `TITLEOFCLASS` matches the stock-like definition above.
- `stock_aum` must sum VALUE only across those stock-like rows.
- `top3_cusips_by_value` must list the 3 stock CUSIPs with the largest summed VALUE for that filing, ordered from largest to smallest.
- Use numbers for numeric fields, not strings.
- Write only the JSON file requested.