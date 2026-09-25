from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Refund Summary",
    "Enterprise Refunds #2215",
    "SMB Refunds #2218"
  ],
  "summary": {
    "sheet_name": "Refund Summary",
    "company": "Atlas Cloud Commerce",
    "title": "Refund Reserve Summary",
    "period_text": "For the period ending 11/30/2025",
    "total_label": "Total refund reserve balance at 11/30/2025"
  },
  "details": [
    {
      "sheet_name": "Enterprise Refunds #2215",
      "company": "Atlas Cloud Commerce",
      "title": "Enterprise Refund Reserve #2215 as of 11/30/2025",
      "subtitle": "Refund reserve activity from August through November 2025",
      "entity_header": "Customer",
      "term_header": "Reserve Months",
      "notes_header": "Notes",
      "account_header": "Reserve Account",
      "totals_label": "Period Totals",
      "gl_key": "enterprise_refunds_2215",
      "months": [
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        },
        {
          "slug": "nov",
          "label": "Nov",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        }
      ],
      "summary_labels": {
        "section": "Enterprise Refund Reserve (Acct 2215)",
        "total": "Enterprise refund accruals in period",
        "ending": "Enterprise credits issued in period",
        "gl": "Enterprise refund GL balance at 11/30/2025"
      }
    },
    {
      "sheet_name": "SMB Refunds #2218",
      "company": "Atlas Cloud Commerce",
      "title": "SMB Refund Reserve #2218 as of 11/30/2025",
      "subtitle": "Refund reserve activity from August through November 2025",
      "entity_header": "Customer",
      "term_header": "Reserve Months",
      "notes_header": "Notes",
      "account_header": "Reserve Account",
      "totals_label": "Period Totals",
      "gl_key": "smb_refunds_2218",
      "months": [
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        },
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        },
        {
          "slug": "nov",
          "label": "Nov",
          "adds_subheader": "Refund Accruals",
          "release_subheader": "Credits Issued"
        }
      ],
      "summary_labels": {
        "section": "SMB Refund Reserve (Acct 2218)",
        "total": "SMB refund accruals in period",
        "ending": "SMB credits issued in period",
        "gl": "SMB refund GL balance at 11/30/2025"
      }
    }
  ]
}

GL_MAP = {
  "enterprise_refunds_2215": {
    "aug": 7500.0,
    "sep": 12500.0,
    "oct": 9250.0,
    "nov": 5000.0
  },
  "smb_refunds_2218": {
    "aug": 4000.0,
    "sep": 6750.0,
    "oct": 5250.0,
    "nov": 4250.0
  }
}

MONTHS = ["aug", "sep", "oct", "nov"]



def normalize_flows(beginning_balance: float, flow_months: dict) -> dict:
    running = float(beginning_balance)
    normalized = {}
    for slug in MONTHS:
        month_flow = flow_months.get(slug, {})
        adds = float(month_flow.get('accrued', 0) or 0)
        release = float(month_flow.get('credited', 0) or 0)
        running = round(running + adds - release, 2)
        normalized[slug] = {'adds': adds, 'release': release, 'ending_balance': running}
    return normalized


def apply_patch(row: dict, patch: dict) -> None:
    if patch['customer_name']:
        row['entity'] = patch['customer_name']
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


def recompute_endings(row: dict) -> None:
    running = float(row['beginning_balance'])
    for slug in MONTHS:
        running = round(running + float(row[f'{slug}_adds']) - float(row[f'{slug}_release']), 2)
        row[f'{slug}_ending_balance'] = running


def build_detail_rows(data_root: Path) -> dict:
    payload = json.loads((data_root / 'refund_snapshot.json').read_text())
    detail_rows = {
        'Enterprise Refunds #2215': [],
        'SMB Refunds #2218': [],
    }
    bucket_to_sheet = {
        'enterprise': 'Enterprise Refunds #2215',
        'smb': 'SMB Refunds #2218',
    }
    for segment in payload['segments']:
        latest = {}
        for snapshot in segment['snapshots']:
            if not snapshot['approved'] or snapshot['row_kind'] != 'detail':
                continue
            current = latest.get(snapshot['case_id'])
            if current is None or snapshot['version'] > current['version']:
                latest[snapshot['case_id']] = snapshot
        for case_id, snapshot in latest.items():
            normalized = normalize_flows(snapshot['opening_amount'], snapshot['flow_months'])
            row = {
                'entity': snapshot['customer_name'],
                'beginning_balance': float(snapshot['opening_amount']),
                'term_months': int(snapshot['term_hint']),
                'comments': snapshot['memo_text'],
                'account_number': int(snapshot['account_code']),
                '_case_id': case_id,
            }
            for slug in MONTHS:
                row[f'{slug}_adds'] = normalized[slug]['adds']
                row[f'{slug}_release'] = normalized[slug]['release']
                row[f'{slug}_ending_balance'] = normalized[slug]['ending_balance']
            detail_rows[bucket_to_sheet[segment['bucket']]].append(row)

    with (data_root / 'refund_adjustments.csv').open(newline='', encoding='utf-8') as handle:
        patches = list(csv.DictReader(handle))
    for patch in patches:
        sheet_name = bucket_to_sheet[patch['target_bucket']]
        if patch['action'] == 'override':
            for row in detail_rows[sheet_name]:
                if row['_case_id'] == patch['row_id']:
                    apply_patch(row, patch)
                    break
        elif patch['action'] == 'insert':
            row = {
                'entity': patch['customer_name'],
                'beginning_balance': float(patch['beginning_balance']),
                'term_months': int(float(patch['term_months'])),
                'comments': patch['comments'],
                'account_number': int(float(patch['account_number'])),
                '_case_id': patch['row_id'],
            }
            for slug in MONTHS:
                row[f'{slug}_adds'] = float(patch[f'{slug}_adds'])
                row[f'{slug}_release'] = float(patch[f'{slug}_release'])
            recompute_endings(row)
            detail_rows[sheet_name].append(row)

    for rows in detail_rows.values():
        rows.sort(key=lambda row: (row['entity'], row['_case_id']))
        for row in rows:
            row.pop('_case_id', None)
    return detail_rows

def main() -> None:
    script_dir = Path(__file__).resolve().parent
    task_dir = script_dir.parent
    data_root = Path('/root') if (Path('/root') / 'refund_snapshot.json').exists() else task_dir / 'environment'
    template_path = data_root / 'refund_template.xlsx'
    output_path = Path('/root/Atlas_Refund_Reserve_11-25.xlsx') if data_root == Path('/root') else task_dir / 'Atlas_Refund_Reserve_11-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(template_path) if template_path else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
