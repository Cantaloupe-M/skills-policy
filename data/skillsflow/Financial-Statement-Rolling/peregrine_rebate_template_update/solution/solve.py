from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Rebate Summary",
    "Channel Rebates #6120",
    "MDF Accrual #6125"
  ],
  "summary": {
    "sheet_name": "Rebate Summary",
    "company": "Peregrine Devices",
    "title": "Rebate Rollforward Summary",
    "period_text": "For the period ending 10/31/2025",
    "total_label": "Total rebate balance at 10/31/2025"
  },
  "details": [
    {
      "sheet_name": "Channel Rebates #6120",
      "company": "Peregrine Devices",
      "title": "Channel Rebates #6120 as of 10/31/2025",
      "subtitle": "Rebate activity from July through October 2025",
      "entity_header": "Partner",
      "term_header": "Reserve Months",
      "notes_header": "Notes",
      "account_header": "Expense Account",
      "totals_label": "Period Totals",
      "gl_key": "channel_rebates_6120",
      "months": [
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        }
      ],
      "summary_labels": {
        "section": "Channel Rebates (Acct 6120)",
        "total": "Channel rebate accruals in period",
        "ending": "Channel rebate utilization in period",
        "gl": "Channel rebate GL balance at 10/31/2025"
      }
    },
    {
      "sheet_name": "MDF Accrual #6125",
      "company": "Peregrine Devices",
      "title": "MDF Accrual #6125 as of 10/31/2025",
      "subtitle": "Rebate activity from July through October 2025",
      "entity_header": "Partner",
      "term_header": "Reserve Months",
      "notes_header": "Notes",
      "account_header": "Expense Account",
      "totals_label": "Period Totals",
      "gl_key": "mdf_accrual_6125",
      "months": [
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Accruals",
          "release_subheader": "Utilization"
        }
      ],
      "summary_labels": {
        "section": "MDF Accrual (Acct 6125)",
        "total": "MDF accruals in period",
        "ending": "MDF utilization in period",
        "gl": "MDF GL balance at 10/31/2025"
      }
    }
  ]
}
GL_MAP = {
  "channel_rebates_6120": {
    "jul": 11000.0,
    "aug": 19500.0,
    "sep": 16500.0,
    "oct": 11500.0
  },
  "mdf_accrual_6125": {
    "jul": 7000.0,
    "aug": 11000.0,
    "sep": 8750.0,
    "oct": 7500.0
  }
}
MONTHS = ["jul", "aug", "sep", "oct"]
INPUT_FILES = {
  "Channel Rebates #6120": "channel_rebate_base.csv",
  "MDF Accrual #6125": "mdf_base.csv"
}



def csv_row_to_detail(raw: dict) -> dict:
    row = {
        'entity': raw['partner'],
        'beginning_balance': float(raw['beginning_balance']),
        'term_months': int(float(raw['term_months'])),
        'comments': raw['comments'],
        'account_number': int(float(raw['account_number'])),
        '_row_key': raw['row_key'],
    }
    for slug in MONTHS:
        row[f'{slug}_adds'] = float(raw[f'{slug}_adds'])
        row[f'{slug}_release'] = float(raw[f'{slug}_release'])
        row[f'{slug}_ending_balance'] = float(raw[f'{slug}_ending_balance'])
    return row


def update_from_patch(row: dict, patch: dict) -> None:
    if patch['partner']:
        row['entity'] = patch['partner']
    if patch['beginning_balance']:
        row['beginning_balance'] = float(patch['beginning_balance'])
    if patch['term_months']:
        row['term_months'] = int(float(patch['term_months']))
    if patch['comments']:
        row['comments'] = patch['comments']
    if patch['account_number']:
        row['account_number'] = int(float(patch['account_number']))
    for slug in MONTHS:
        add_key = f'{slug}_adds'
        rel_key = f'{slug}_release'
        end_key = f'{slug}_ending_balance'
        if patch[add_key]:
            row[add_key] = float(patch[add_key])
        if patch[rel_key]:
            row[rel_key] = float(patch[rel_key])
        if patch[end_key]:
            row[end_key] = float(patch[end_key])


def build_from_csv(path: Path) -> list[dict]:
    rows = []
    with path.open(newline='', encoding='utf-8') as handle:
        for raw in csv.DictReader(handle):
            if raw['status'] != 'open':
                continue
            rows.append(csv_row_to_detail(raw))
    return rows


def build_detail_rows(data_root: Path) -> dict:
    detail_rows = {
        'Channel Rebates #6120': build_from_csv(data_root / 'channel_rebate_base.csv'),
        'MDF Accrual #6125': build_from_csv(data_root / 'mdf_base.csv'),
    }
    patches = []
    with (data_root / 'schedule_patch.csv').open(newline='', encoding='utf-8') as handle:
        patches = list(csv.DictReader(handle))

    for patch in patches:
        target_sheet = patch['target_sheet']
        if patch['action'] == 'override':
            for row in detail_rows[target_sheet]:
                if row['_row_key'] == patch['row_key']:
                    update_from_patch(row, patch)
                    break
        elif patch['action'] == 'insert':
            inserted = {
                'entity': patch['partner'],
                'beginning_balance': float(patch['beginning_balance']),
                'term_months': int(float(patch['term_months'])),
                'comments': patch['comments'],
                'account_number': int(float(patch['account_number'])),
                '_row_key': patch['row_key'],
            }
            for slug in MONTHS:
                inserted[f'{slug}_adds'] = float(patch[f'{slug}_adds'])
                inserted[f'{slug}_release'] = float(patch[f'{slug}_release'])
                inserted[f'{slug}_ending_balance'] = float(patch[f'{slug}_ending_balance'])
            detail_rows[target_sheet].append(inserted)

    for rows in detail_rows.values():
        rows.sort(key=lambda row: (row['entity'], row['_row_key']))
        for row in rows:
            row.pop('_row_key', None)
    return detail_rows


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    task_dir = script_dir.parent
    data_root = Path('/root') if (Path('/root') / list(INPUT_FILES.values())[0]).exists() or (Path('/root') / 'project_cost_rollforward.json').exists() or (Path('/root') / 'rebate_template.xlsx').exists() else task_dir / 'environment'
    available_files = {path.name for path in data_root.iterdir()}
    TEMPLATE_PATH = data_root / 'rebate_template.xlsx' if 'rebate_template.xlsx' in available_files else None
    output_path = Path('/root/Peregrine_Rebate_Rollforward_10-25.xlsx') if data_root == Path('/root') else task_dir / 'Peregrine_Rebate_Rollforward_10-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(TEMPLATE_PATH) if TEMPLATE_PATH else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
