from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Contract Liability Summary",
    "Subscriptions #2350",
    "Services #2355"
  ],
  "summary": {
    "sheet_name": "Contract Liability Summary",
    "company": "Meridian Mobility Network",
    "title": "Contract Liability Summary",
    "period_text": "For the period ending 12/31/2025",
    "total_label": "Total contract liability balance at 12/31/2025"
  },
  "details": [
    {
      "sheet_name": "Subscriptions #2350",
      "company": "Meridian Mobility Network",
      "title": "Subscription Contract Liability #2350 as of 12/31/2025",
      "subtitle": "Contract liability activity from September through December 2025",
      "entity_header": "Customer",
      "term_header": "Contract Months",
      "notes_header": "Notes",
      "account_header": "Liability Account",
      "totals_label": "Period Totals",
      "gl_key": "subscriptions_2350",
      "months": [
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        },
        {
          "slug": "nov",
          "label": "Nov",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        },
        {
          "slug": "dec",
          "label": "Dec",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        }
      ],
      "summary_labels": {
        "section": "Subscription Contract Liability (Acct 2350)",
        "total": "Subscription billings in period",
        "ending": "Subscription revenue recognized in period",
        "gl": "Subscription GL balance at 12/31/2025"
      }
    },
    {
      "sheet_name": "Services #2355",
      "company": "Meridian Mobility Network",
      "title": "Services Contract Liability #2355 as of 12/31/2025",
      "subtitle": "Contract liability activity from September through December 2025",
      "entity_header": "Customer",
      "term_header": "Contract Months",
      "notes_header": "Notes",
      "account_header": "Liability Account",
      "totals_label": "Period Totals",
      "gl_key": "services_2355",
      "months": [
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        },
        {
          "slug": "nov",
          "label": "Nov",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        },
        {
          "slug": "dec",
          "label": "Dec",
          "adds_subheader": "Billings",
          "release_subheader": "Revenue"
        }
      ],
      "summary_labels": {
        "section": "Services Contract Liability (Acct 2355)",
        "total": "Services billings in period",
        "ending": "Services revenue recognized in period",
        "gl": "Services GL balance at 12/31/2025"
      }
    }
  ]
}

GL_MAP = {
  "subscriptions_2350": {
    "sep": 21000.0,
    "oct": 26000.0,
    "nov": 20000.0,
    "dec": 11000.0
  },
  "services_2355": {
    "sep": 12000.0,
    "oct": 14750.0,
    "nov": 10000.0,
    "dec": 6250.0
  }
}

MONTHS = ["sep", "oct", "nov", "dec"]



def normalize_sparse_months(beginning_balance: float, month_roll: dict) -> dict:
    running = float(beginning_balance)
    normalized = {}
    for slug in MONTHS:
        month_data = month_roll.get(slug, {})
        adds = float(month_data.get('booked', 0) or 0)
        release = float(month_data.get('earned', 0) or 0)
        running = round(running + adds - release, 2)
        normalized[slug] = {'adds': adds, 'release': release, 'ending_balance': running}
    return normalized


def recompute_endings(row: dict) -> None:
    running = float(row['beginning_balance'])
    for slug in MONTHS:
        running = round(running + float(row[f'{slug}_adds']) - float(row[f'{slug}_release']), 2)
        row[f'{slug}_ending_balance'] = running


def apply_bridge(row: dict, patch: dict) -> None:
    if patch['party_name']:
        row['entity'] = patch['party_name']
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
        release_key = f'{slug}_release'
        if patch[add_key]:
            row[add_key] = float(patch[add_key])
        if patch[release_key]:
            row[release_key] = float(patch[release_key])
    recompute_endings(row)


def build_detail_rows(data_root: Path) -> dict:
    aliases = {}
    with (data_root / 'bucket_aliases.csv').open(newline='', encoding='utf-8') as handle:
        for raw in csv.DictReader(handle):
            aliases[raw['source_bucket']] = raw

    payload = json.loads((data_root / 'contract_liability_dump.json').read_text())
    detail_rows = {cfg['sheet_name']: [] for cfg in aliases.values()}
    for export in payload['exports']:
        alias = aliases[export['source_bucket']]
        latest = {}
        for cluster in export['clusters']:
            for record in cluster['records']:
                if not record['active_flag'] or record['record_type'] != 'detail':
                    continue
                current = latest.get(record['contract_key'])
                if current is None or record['revision_no'] > current['revision_no']:
                    latest[record['contract_key']] = record
        for contract_key, record in latest.items():
            normalized = normalize_sparse_months(record['opening_amount'], record['month_roll'])
            row = {
                'entity': record['party_name'],
                'beginning_balance': float(record['opening_amount']),
                'term_months': int(record['term_hint']),
                'comments': record['memo_label'],
                'account_number': int(alias['account_number']),
                '_contract_key': contract_key,
                '_source_bucket': export['source_bucket'],
            }
            for slug in MONTHS:
                row[f'{slug}_adds'] = normalized[slug]['adds']
                row[f'{slug}_release'] = normalized[slug]['release']
                row[f'{slug}_ending_balance'] = normalized[slug]['ending_balance']
            detail_rows[alias['sheet_name']].append(row)

    with (data_root / 'manual_bridge.csv').open(newline='', encoding='utf-8') as handle:
        bridge_rows = list(csv.DictReader(handle))
    for patch in bridge_rows:
        alias = aliases[patch['source_bucket']]
        sheet_name = alias['sheet_name']
        if patch['action'] == 'override':
            for row in detail_rows[sheet_name]:
                if row['_contract_key'] == patch['contract_key']:
                    apply_bridge(row, patch)
                    break
        elif patch['action'] == 'insert':
            row = {
                'entity': patch['party_name'],
                'beginning_balance': float(patch['beginning_balance']),
                'term_months': int(float(patch['term_months'])),
                'comments': patch['comments'],
                'account_number': int(float(patch['account_number'])),
                '_contract_key': patch['contract_key'],
                '_source_bucket': patch['source_bucket'],
            }
            for slug in MONTHS:
                row[f'{slug}_adds'] = float(patch[f'{slug}_adds'])
                row[f'{slug}_release'] = float(patch[f'{slug}_release'])
            recompute_endings(row)
            detail_rows[sheet_name].append(row)

    for rows in detail_rows.values():
        rows.sort(key=lambda row: (row['entity'], row['_contract_key']))
        for row in rows:
            row.pop('_contract_key', None)
            row.pop('_source_bucket', None)
    return detail_rows

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    task_dir = script_dir.parent
    data_root = Path('/root') if (Path('/root') / 'contract_liability_dump.json').exists() else task_dir / 'environment'
    template_path = data_root / 'liability_template.xlsx'
    output_path = Path('/root/Meridian_Contract_Liability_12-25.xlsx') if data_root == Path('/root') else task_dir / 'Meridian_Contract_Liability_12-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(template_path) if template_path else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
