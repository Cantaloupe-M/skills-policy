from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Project Cost Summary",
    "Cap Impl #1460",
    "Leasehold #1465"
  ],
  "summary": {
    "sheet_name": "Project Cost Summary",
    "company": "Orchid Health Systems",
    "title": "Project Cost Rollforward Summary",
    "period_text": "For the period ending 9/30/2025",
    "total_label": "Total project cost balance at 9/30/2025"
  },
  "details": [
    {
      "sheet_name": "Cap Impl #1460",
      "company": "Orchid Health Systems",
      "title": "Capitalized Implementation Costs #1460 as of 9/30/2025",
      "subtitle": "Project cost activity from June through September 2025",
      "entity_header": "Vendor",
      "term_header": "Useful Life Months",
      "notes_header": "Notes",
      "account_header": "Source Account",
      "totals_label": "Period Totals",
      "gl_key": "cap_impl_1460",
      "months": [
        {
          "slug": "jun",
          "label": "Jun",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        },
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        }
      ],
      "summary_labels": {
        "section": "Capitalized Implementation Costs (Acct 1460)",
        "total": "Capitalized adds booked in period",
        "ending": "Amortization booked in period",
        "gl": "Implementation GL balance at 9/30/2025"
      }
    },
    {
      "sheet_name": "Leasehold #1465",
      "company": "Orchid Health Systems",
      "title": "Leasehold Improvements #1465 as of 9/30/2025",
      "subtitle": "Project cost activity from June through September 2025",
      "entity_header": "Vendor",
      "term_header": "Useful Life Months",
      "notes_header": "Notes",
      "account_header": "Source Account",
      "totals_label": "Period Totals",
      "gl_key": "leasehold_1465",
      "months": [
        {
          "slug": "jun",
          "label": "Jun",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        },
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Cap Adds",
          "release_subheader": "Amortization"
        }
      ],
      "summary_labels": {
        "section": "Leasehold Improvements (Acct 1465)",
        "total": "Leasehold adds booked in period",
        "ending": "Leasehold amortization in period",
        "gl": "Leasehold GL balance at 9/30/2025"
      }
    }
  ]
}
GL_MAP = {
  "cap_impl_1460": {
    "jun": 32375.0,
    "jul": 40875.0,
    "aug": 40375.0,
    "sep": 29875.0
  },
  "leasehold_1465": {
    "jun": 16500.0,
    "jul": 22000.0,
    "aug": 24750.0,
    "sep": 25000.0
  }
}
MONTHS = ["jun", "jul", "aug", "sep"]
INPUT_FILES = {
  "Cap Impl #1460": "project_cost_rollforward.json",
  "Leasehold #1465": "project_cost_rollforward.json"
}



def apply_override(row: dict, override: dict) -> None:
    if override['notes_override']:
        row['comments'] = override['notes_override']
    for slug in MONTHS[1:]:
        add_key = f'{slug}_adds'
        rel_key = f'{slug}_release'
        end_key = f'{slug}_ending_balance'
        if override.get(add_key):
            row[add_key] = float(override[add_key])
        if override.get(rel_key):
            row[rel_key] = float(override[rel_key])
        if override.get(end_key):
            row[end_key] = float(override[end_key])


def flatten_item(item: dict) -> dict:
    row = {
        'entity': item['vendor_name'],
        'beginning_balance': float(item['opening_balance']),
        'term_months': int(item['useful_life_months']),
        'comments': item['memo'],
        'account_number': int(item['source_account']),
    }
    for slug in MONTHS:
        month_data = item['months'][slug]
        row[f'{slug}_adds'] = float(month_data['adds'])
        row[f'{slug}_release'] = float(month_data['release'])
        row[f'{slug}_ending_balance'] = float(month_data['ending_balance'])
    row['_row_id'] = item['row_id']
    return row


def build_detail_rows(data_root: Path) -> dict:
    source = json.loads((data_root / 'project_cost_rollforward.json').read_text())
    overrides = {}
    with (data_root / 'schedule_overrides.csv').open(newline='', encoding='utf-8') as handle:
        for raw in csv.DictReader(handle):
            overrides[raw['row_id']] = raw

    detail_rows = {}
    for account in source['accounts']:
        latest = {}
        for group in account['groups']:
            for item in group['items']:
                if not item['active']:
                    continue
                current = latest.get(item['row_id'])
                if current is None or item['revision'] > current['revision']:
                    latest[item['row_id']] = item
        rows = []
        for row_id, item in latest.items():
            row = flatten_item(item)
            if row_id in overrides:
                apply_override(row, overrides[row_id])
            rows.append(row)
        rows.sort(key=lambda row: (row['entity'], row['_row_id']))
        for row in rows:
            row.pop('_row_id', None)
        detail_rows[account['sheet_name']] = rows
    return detail_rows


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    task_dir = script_dir.parent
    data_root = Path('/root') if (Path('/root') / list(INPUT_FILES.values())[0]).exists() or (Path('/root') / 'project_cost_rollforward.json').exists() or (Path('/root') / 'rebate_template.xlsx').exists() else task_dir / 'environment'
    available_files = {path.name for path in data_root.iterdir()}
    TEMPLATE_PATH = None
    output_path = Path('/root/Orchid_Project_Costs_9-25.xlsx') if data_root == Path('/root') else task_dir / 'Orchid_Project_Costs_9-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(TEMPLATE_PATH) if TEMPLATE_PATH else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
