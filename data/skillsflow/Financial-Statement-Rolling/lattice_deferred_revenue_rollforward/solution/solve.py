from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Deferred Summary",
    "SaaS Rev #2300",
    "Services Rev #2310"
  ],
  "summary": {
    "sheet_name": "Deferred Summary",
    "company": "LatticeWare",
    "title": "Deferred Revenue Summary",
    "period_text": "For the period ending 8/31/2025",
    "total_label": "Total deferred revenue balance at 8/31/2025"
  },
  "details": [
    {
      "sheet_name": "SaaS Rev #2300",
      "company": "LatticeWare",
      "title": "SaaS Deferred Revenue #2300 as of 8/31/2025",
      "subtitle": "Deferred revenue activity from May through August 2025",
      "entity_header": "Customer",
      "term_header": "Contract Months",
      "notes_header": "Notes",
      "account_header": "Revenue Code",
      "totals_label": "Period Totals",
      "gl_key": "saas_rev_2300",
      "months": [
        {
          "slug": "may",
          "label": "May",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        },
        {
          "slug": "jun",
          "label": "Jun",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        },
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        }
      ],
      "summary_labels": {
        "section": "SaaS Deferred Revenue (Acct 2300)",
        "total": "SaaS billings booked in period",
        "ending": "SaaS revenue recognized in period",
        "gl": "SaaS GL balance at 8/31/2025"
      }
    },
    {
      "sheet_name": "Services Rev #2310",
      "company": "LatticeWare",
      "title": "Services Deferred Revenue #2310 as of 8/31/2025",
      "subtitle": "Deferred revenue activity from May through August 2025",
      "entity_header": "Customer",
      "term_header": "Contract Months",
      "notes_header": "Notes",
      "account_header": "Revenue Code",
      "totals_label": "Period Totals",
      "gl_key": "services_rev_2310",
      "months": [
        {
          "slug": "may",
          "label": "May",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        },
        {
          "slug": "jun",
          "label": "Jun",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        },
        {
          "slug": "jul",
          "label": "Jul",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        },
        {
          "slug": "aug",
          "label": "Aug",
          "adds_subheader": "Billings",
          "release_subheader": "Recognition"
        }
      ],
      "summary_labels": {
        "section": "Services Deferred Revenue (Acct 2310)",
        "total": "Services billings booked in period",
        "ending": "Services revenue recognized in period",
        "gl": "Services GL balance at 8/31/2025"
      }
    }
  ]
}
GL_MAP = {
  "saas_rev_2300": {
    "may": 81000.0,
    "jun": 88500.0,
    "jul": 63000.0,
    "aug": 36500.0
  },
  "services_rev_2310": {
    "may": 16750.0,
    "jun": 21500.0,
    "jul": 16250.0,
    "aug": 4000.0
  }
}
MONTHS = ["may", "jun", "jul", "aug"]
INPUT_FILES = {
  "SaaS Rev #2300": "saas_deferred_revenue_schedule.csv",
  "Services Rev #2310": "services_deferred_revenue_schedule.csv"
}



def read_csv_rows(path: Path) -> list[dict]:
    with path.open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle)
        rows = []
        for raw in reader:
            row = {
                'entity': raw['entity'],
                'beginning_balance': float(raw['beginning_balance']),
                'term_months': int(float(raw['term_months'])),
                'comments': raw['comments'],
                'account_number': int(float(raw['account_number'])),
            }
            for slug in MONTHS:
                row[f'{slug}_adds'] = float(raw[f'{slug}_adds'])
                row[f'{slug}_release'] = float(raw[f'{slug}_release'])
                row[f'{slug}_ending_balance'] = float(raw[f'{slug}_ending_balance'])
            rows.append(row)
        return rows


def build_detail_rows(data_root: Path) -> dict:
    detail_rows = {}
    for sheet_name, filename in INPUT_FILES.items():
        detail_rows[sheet_name] = read_csv_rows(data_root / filename)
    return detail_rows


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    task_dir = script_dir.parent
    data_root = Path('/root') if (Path('/root') / list(INPUT_FILES.values())[0]).exists() or (Path('/root') / 'project_cost_rollforward.json').exists() or (Path('/root') / 'rebate_template.xlsx').exists() else task_dir / 'environment'
    available_files = {path.name for path in data_root.iterdir()}
    TEMPLATE_PATH = None
    output_path = Path('/root/LatticeWare_Deferred_Revenue_8-25.xlsx') if data_root == Path('/root') else task_dir / 'LatticeWare_Deferred_Revenue_8-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(TEMPLATE_PATH) if TEMPLATE_PATH else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
