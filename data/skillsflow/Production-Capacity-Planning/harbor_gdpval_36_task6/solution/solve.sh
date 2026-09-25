#!/bin/bash
set -euo pipefail

cat > /tmp/build_plan.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import Workbook, load_workbook

INPUT_XLSX = Path("/root/dye_demand_sheet.xlsx")
OUTPUT_XLSX = Path("/root/dye_catch_up_plan.xlsx")
OUTPUT_SUMMARY = Path("/root/dye_catch_up_summary.txt")

WEEK_START = 3
WEEK_END = 51
INITIAL_WEEK3_TOTAL = 598.24
RATE_PER_DAY = 18.0


def _clean_label(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _read_sheet(ws, row_label: str) -> Dict[int, float]:
    """Read a sheet and return {week: value} from the row matching row_label."""
    week_col = None
    val_col = None
    header = list(ws.iter_rows(min_row=1, max_row=1, values_only=True))[0]
    for idx, val in enumerate(header):
        if _clean_label(val) == "week":
            week_col = idx
        elif _clean_label(val) == row_label:
            val_col = idx
    if week_col is None:
        raise ValueError(f"Could not find 'Week' column in sheet")
    if val_col is None:
        raise ValueError(f"Could not find row labeled '{row_label}'")

    out: Dict[int, float] = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        wv = row[week_col]
        vv = row[val_col]
        if wv is None or vv is None:
            continue
        try:
            week = int(round(float(wv)))
            val = float(vv)
        except (TypeError, ValueError):
            continue
        out[week] = val
    return out


def load_weekly_demand(path: Path) -> List[Tuple[int, float]]:
    wb = load_workbook(path, data_only=True)

    dye_ws = wb["Dye"] if "Dye" in wb.sheetnames else wb.active
    adjust_ws = wb["Adjust"] if "Adjust" in wb.sheetnames else wb.active

    dye_demands = _read_sheet(dye_ws, "dye demand (std hrs)")
    adjust_demands = _read_sheet(adjust_ws, "demand adjustment (std hrs)")

    # Effective demand = Dye + Adjustment
    all_weeks = set(dye_demands.keys()) & set(adjust_demands.keys())

    missing = [w for w in range(WEEK_START, WEEK_END + 1) if w not in all_weeks]
    if missing:
        raise ValueError(f"Missing demand values for weeks: {missing}")

    return [(w, dye_demands[w] + adjust_demands[w]) for w in range(WEEK_START, WEEK_END + 1)]


def choose_days(calc_start: float, demand: float) -> int:
    start_past_due = max(0.0, calc_start)
    if start_past_due > 0.01:
        for days in (5, 6):
            if calc_start + demand - (RATE_PER_DAY * days) <= 0.0:
                return days
        return 6

    if demand <= 72.0:
        return 4
    return 5


def build_plan() -> List[Tuple[int, int, float, float, float, float, float]]:
    demand_data = load_weekly_demand(INPUT_XLSX)

    week3_demand = demand_data[0][1]
    calc_start = INITIAL_WEEK3_TOTAL - week3_demand

    rows: List[Tuple[int, int, float, float, float, float, float]] = []
    for week, demand in demand_data:
        days = choose_days(calc_start, demand)
        capacity = RATE_PER_DAY * days
        start_past_due = max(0.0, calc_start)
        end_backlog_buffer = calc_start + demand - capacity
        overtime = 10.0 * max(0, days - 4)

        rows.append(
            (
                week,
                days,
                demand,
                capacity,
                start_past_due,
                end_backlog_buffer,
                overtime,
            )
        )

        calc_start = end_backlog_buffer

    return rows


def save_workbook(rows: List[Tuple[int, int, float, float, float, float, float]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Plan"

    headers = [
        "Week",
        "Days Worked",
        "Scheduled Demand (Std Hrs)",
        "Weekly Capacity (Std Hrs)",
        "Start of Week Past Due (Std Hrs)",
        "End of Week Backlog/Buffer (Std Hrs)",
        "Overtime Hours",
    ]
    ws.append(headers)

    for row in rows:
        ws.append(list(row))

    for r in range(2, 2 + len(rows)):
        ws.cell(r, 1).number_format = "0"
        ws.cell(r, 2).number_format = "0"
        for c in (3, 4, 5, 6, 7):
            ws.cell(r, c).number_format = "0.00"

    wb.save(OUTPUT_XLSX)


def save_summary(rows: List[Tuple[int, int, float, float, float, float, float]]) -> None:
    first_week_5 = next((week for week, days, *_ in rows if days == 5), None)
    first_week_4 = next((week for week, days, *_ in rows if days == 4), None)

    fw5 = str(first_week_5) if first_week_5 is not None else "N/A"
    fw4 = str(first_week_4) if first_week_4 is not None else "N/A"

    summary = (
        f"Shift to 5 days in Week {fw5} and to 4 days in Week {fw4}. "
        "Before catch-up, use 5 or 6 days based on backlog clearance. "
        "After catch-up, hold 4 days when weekly demand is 72 hours or lower."
    )

    lines = [
        f"First_Week_5_Days: {fw5}",
        f"First_Week_4_Days: {fw4}",
        f"Summary: {summary}",
    ]
    OUTPUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = build_plan()
    save_workbook(rows)
    save_summary(rows)
    print(f"Wrote {OUTPUT_XLSX}")
    print(f"Wrote {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /tmp/build_plan.py
