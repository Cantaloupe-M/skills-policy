from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.rollforward_builder import write_workbook

SPEC = {
  "sheet_order": [
    "Accrual Summary",
    "Payroll Accrual #2105",
    "Bonus Accrual #2110"
  ],
  "summary": {
    "sheet_name": "Accrual Summary",
    "company": "Cedar Ridge Manufacturing",
    "title": "Accrual Rollforward Summary",
    "period_text": "For the period ending 11/30/2025",
    "total_label": "Total accrual balance at 11/30/2025"
  },
  "details": [
    {
      "sheet_name": "Payroll Accrual #2105",
      "company": "Cedar Ridge Manufacturing",
      "title": "Payroll Accrual #2105 as of 11/30/2025",
      "subtitle": "Accrual activity from September through November 2025",
      "entity_header": "Accrual Bucket",
      "term_header": "Reserve Months",
      "notes_header": "Notes",
      "account_header": "Department Code",
      "totals_label": "Period Totals",
      "gl_key": "payroll_accrual_2105",
      "months": [
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Accruals",
          "release_subheader": "Releases"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Accruals",
          "release_subheader": "Releases"
        },
        {
          "slug": "nov",
          "label": "Nov",
          "adds_subheader": "Accruals",
          "release_subheader": "Releases"
        }
      ],
      "summary_labels": {
        "section": "Payroll Accrual (Acct 2105)",
        "total": "Payroll accruals booked in period",
        "ending": "Payroll releases in period",
        "gl": "Payroll GL balance at 11/30/2025"
      }
    },
    {
      "sheet_name": "Bonus Accrual #2110",
      "company": "Cedar Ridge Manufacturing",
      "title": "Bonus Accrual #2110 as of 11/30/2025",
      "subtitle": "Accrual activity from September through November 2025",
      "entity_header": "Accrual Bucket",
      "term_header": "Reserve Months",
      "notes_header": "Notes",
      "account_header": "Department Code",
      "totals_label": "Period Totals",
      "gl_key": "bonus_accrual_2110",
      "months": [
        {
          "slug": "sep",
          "label": "Sep",
          "adds_subheader": "Accruals",
          "release_subheader": "Releases"
        },
        {
          "slug": "oct",
          "label": "Oct",
          "adds_subheader": "Accruals",
          "release_subheader": "Releases"
        },
        {
          "slug": "nov",
          "label": "Nov",
          "adds_subheader": "Accruals",
          "release_subheader": "Releases"
        }
      ],
      "summary_labels": {
        "section": "Bonus Accrual (Acct 2110)",
        "total": "Bonus accruals booked in period",
        "ending": "Bonus releases in period",
        "gl": "Bonus GL balance at 11/30/2025"
      }
    }
  ]
}
GL_MAP = {
  "payroll_accrual_2105": {
    "sep": 3500.0,
    "oct": 4600.0,
    "nov": 5700.0
  },
  "bonus_accrual_2110": {
    "sep": 17000.0,
    "oct": 31000.0,
    "nov": 50400.0
  }
}
MONTHS = ["sep", "oct", "nov"]
INPUT_FILES = {
  "Payroll Accrual #2105": "payroll_accrual_schedule.csv",
  "Bonus Accrual #2110": "bonus_accrual_schedule.csv"
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
    output_path = Path('/root/CedarRidge_Accrual_Rollforward_11-25.xlsx') if data_root == Path('/root') else task_dir / 'CedarRidge_Accrual_Rollforward_11-25.xlsx'
    detail_rows = build_detail_rows(data_root)
    write_workbook(SPEC, detail_rows, GL_MAP, str(output_path), str(TEMPLATE_PATH) if TEMPLATE_PATH else None)
    print(f'Wrote {output_path}')

if __name__ == '__main__':
    main()
