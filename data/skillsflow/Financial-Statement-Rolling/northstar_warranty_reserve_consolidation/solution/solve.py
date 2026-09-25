from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Warranty Summary",
    "Consumer Warranty #2440",
    "Commercial Warranty #2445"
  ],
  "summary": {
    "sheet_name": "Warranty Summary",
    "company": "Northstar Appliances",
    "title": "Warranty Reserve Summary",
    "period_text": "For the period ending 9/30/2025",
    "total_label": "Total warranty reserve balance at 9/30/2025"
  },
  "details": [
    {
      "sheet_name": "Consumer Warranty #2440",
      "company": "Northstar Appliances",
      "title": "Consumer Warranty Reserve #2440 as of 9/30/2025",
      "subtitle": "Warranty reserve activity from June through September 2025",
      "entity_header": "Claim Group",
      "term_header": "Coverage Months",
      "notes_header": "Notes",
      "account_header": "Reserve Account",
      "totals_label": "Period Totals",
      "gl_key": "consumer_warranty_2440",
      "months": [
        {
          "slug": "jun",
          "label": "Jun",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        },
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        }
      ],
      "summary_labels": {
        "section": "Consumer Warranty Reserve (Acct 2440)",
        "total": "Consumer accruals booked in period",
        "ending": "Consumer claims paid in period",
        "gl": "Consumer GL balance at 9/30/2025"
      }
    },
    {
      "sheet_name": "Commercial Warranty #2445",
      "company": "Northstar Appliances",
      "title": "Commercial Warranty Reserve #2445 as of 9/30/2025",
      "subtitle": "Warranty reserve activity from June through September 2025",
      "entity_header": "Claim Group",
      "term_header": "Coverage Months",
      "notes_header": "Notes",
      "account_header": "Reserve Account",
      "totals_label": "Period Totals",
      "gl_key": "commercial_warranty_2445",
      "months": [
        {
          "slug": "jun",
          "label": "Jun",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        },
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Accruals",
          "release_subheader": "Claims Paid"
        }
      ],
      "summary_labels": {
        "section": "Commercial Warranty Reserve (Acct 2445)",
        "total": "Commercial accruals booked in period",
        "ending": "Commercial claims paid in period",
        "gl": "Commercial GL balance at 9/30/2025"
      }
    }
  ]
}

GL_MAP = {
  "consumer_warranty_2440": {
    "jun": 15000.0,
    "jul": 17500.0,
    "aug": 13500.0,
    "sep": 7500.0
  },
  "commercial_warranty_2445": {
    "jun": 23500.0,
    "jul": 33500.0,
    "aug": 23250.0,
    "sep": 10000.0
  }
}

MONTHS = ["jun", "jul", "aug", "sep"]



def build_detail_rows(data_root: Path) -> dict:
    account_map = json.loads((data_root / 'reserve_account_map.json').read_text())
    detail_rows = {cfg['sheet_name']: [] for cfg in account_map.values()}
    with (data_root / 'warranty_reserve_combined.csv').open(newline='', encoding='utf-8') as handle:
        for raw in csv.DictReader(handle):
            if raw['record_status'] != 'active':
                continue
            sheet_name = account_map[raw['bucket_code']]['sheet_name']
            row = {
                'entity': raw['claim_group'],
                'beginning_balance': float(raw['opening_reserve']),
                'term_months': int(float(raw['coverage_months'])),
                'comments': raw['explanation'],
                'account_number': int(float(raw['gl_code'])),
            }
            for slug in MONTHS:
                row[f'{slug}_adds'] = float(raw[f'{slug}_incurred'])
                row[f'{slug}_release'] = float(raw[f'{slug}_paid'])
                row[f'{slug}_ending_balance'] = float(raw[f'{slug}_close'])
            detail_rows[sheet_name].append(row)
    for rows in detail_rows.values():
        rows.sort(key=lambda row: row['entity'])
    return detail_rows

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    task_dir = script_dir.parent
    data_root = Path('/root') if (Path('/root') / 'warranty_reserve_combined.csv').exists() else task_dir / 'environment'
    template_path = None
    output_path = Path('/root/Northstar_Warranty_Reserve_9-25.xlsx') if data_root == Path('/root') else task_dir / 'Northstar_Warranty_Reserve_9-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(template_path) if template_path else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
