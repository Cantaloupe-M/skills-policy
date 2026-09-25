from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Commission Asset Summary",
    "Field Comm Asset #1510",
    "Partner Comm Asset #1515"
  ],
  "summary": {
    "sheet_name": "Commission Asset Summary",
    "company": "Solstice Energy Software",
    "title": "Commission Asset Rollforward Summary",
    "period_text": "For the period ending 10/31/2025",
    "total_label": "Total commission asset balance at 10/31/2025"
  },
  "details": [
    {
      "sheet_name": "Field Comm Asset #1510",
      "company": "Solstice Energy Software",
      "title": "Field Commission Asset #1510 as of 10/31/2025",
      "subtitle": "Commission asset activity from July through October 2025",
      "entity_header": "Payee",
      "term_header": "Useful Life Months",
      "notes_header": "Notes",
      "account_header": "Asset Account",
      "totals_label": "Period Totals",
      "gl_key": "field_comm_asset_1510",
      "months": [
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        }
      ],
      "summary_labels": {
        "section": "Field Commission Asset (Acct 1510)",
        "total": "Field commissions capitalized in period",
        "ending": "Field amortization in period",
        "gl": "Field commission GL balance at 10/31/2025"
      }
    },
    {
      "sheet_name": "Partner Comm Asset #1515",
      "company": "Solstice Energy Software",
      "title": "Partner Commission Asset #1515 as of 10/31/2025",
      "subtitle": "Commission asset activity from July through October 2025",
      "entity_header": "Payee",
      "term_header": "Useful Life Months",
      "notes_header": "Notes",
      "account_header": "Asset Account",
      "totals_label": "Period Totals",
      "gl_key": "partner_comm_asset_1515",
      "months": [
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Capitalized",
          "release_subheader": "Amortization"
        }
      ],
      "summary_labels": {
        "section": "Partner Commission Asset (Acct 1515)",
        "total": "Partner commissions capitalized in period",
        "ending": "Partner amortization in period",
        "gl": "Partner commission GL balance at 10/31/2025"
      }
    }
  ]
}

GL_MAP = {
  "field_comm_asset_1510": {
    "jul": 18750.0,
    "aug": 22500.0,
    "sep": 17250.0,
    "oct": 12000.0
  },
  "partner_comm_asset_1515": {
    "jul": 20000.0,
    "aug": 22750.0,
    "sep": 20000.0,
    "oct": 13250.0
  }
}

MONTHS = ["jul", "aug", "sep", "oct"]



def build_detail_rows(data_root: Path) -> dict:
    metadata = {}
    with (data_root / 'commission_metadata.csv').open(newline='', encoding='utf-8') as handle:
        for raw in csv.DictReader(handle):
            metadata[raw['line_key']] = raw

    payload = json.loads((data_root / 'commission_activity.json').read_text())
    detail_rows = {
        'Field Comm Asset #1510': [],
        'Partner Comm Asset #1515': [],
    }
    sheet_by_code = {
        'field': 'Field Comm Asset #1510',
        'partner': 'Partner Comm Asset #1515',
    }
    for section in payload['sections']:
        for item in section['rows']:
            if not item['eligible']:
                continue
            meta = metadata.get(item['line_key'])
            if meta is None or meta['sheet_code'] != section['sheet_code']:
                continue
            row = {
                'entity': item['payee_name'],
                'beginning_balance': float(item['opening_amount']),
                'term_months': int(float(meta['useful_life_months'])),
                'comments': meta['narrative'],
                'account_number': int(float(meta['account_number'])),
                '_line_key': item['line_key'],
            }
            for slug in MONTHS:
                row[f'{slug}_adds'] = float(item['activity'][slug]['capitalized'])
                row[f'{slug}_release'] = float(item['activity'][slug]['amortized'])
                row[f'{slug}_ending_balance'] = float(item['activity'][slug]['ending_balance'])
            detail_rows[sheet_by_code[section['sheet_code']]].append(row)
    for rows in detail_rows.values():
        rows.sort(key=lambda row: (row['entity'], row['_line_key']))
        for row in rows:
            row.pop('_line_key', None)
    return detail_rows

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    task_dir = script_dir.parent
    data_root = Path('/root') if (Path('/root') / 'commission_activity.json').exists() else task_dir / 'environment'
    template_path = None
    output_path = Path('/root/Solstice_Commission_Assets_10-25.xlsx') if data_root == Path('/root') else task_dir / 'Solstice_Commission_Assets_10-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(template_path) if template_path else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
