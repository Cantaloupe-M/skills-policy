#!/bin/bash
set -euo pipefail

cat > /tmp/build_plan.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import Workbook

INPUT_CSV = Path("/root/ship_demand.csv")
OUTPUT_XLSX = Path("/root/ship_block_plan.xlsx")
OUTPUT_SUMMARY = Path("/root/ship_block_summary.txt")

WEEK_START = 5
WEEK_END = 53
INITIAL_WEEK5_TOTAL = 1014.51
RATE_PER_DAY = 28.0


def load_weekly_demand(path: Path) -> List[Tuple[int, float]]:
    """
    Read the CSV with transposed layout:
    Row 1: Week,5,6,7,...,53
    Row 2: Demand,d5,d6,d7,...,d53

    We need to transpose: treat column headers as week numbers,
    and the Demand row values as the demand for each week.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if len(rows) < 2:
        raise ValueError("CSV must have at least 2 rows")

    header = rows[0]  # ['Week', '5', '6', '7', ..., '53']
    demand_row = rows[1]  # ['Demand', 'd5', 'd6', ..., 'd53']

    if header[0].strip().lower() != "week":
        raise ValueError("CSV first column must be 'Week'")
    if demand_row[0].strip().lower() != "demand":
        raise ValueError("CSV second row first column must be 'Demand'")

    week_to_demand: Dict[int, float] = {}
    for i in range(1, len(header)):
        h = header[i].strip()
        d = demand_row[i].strip()
        try:
            week = int(h)
            demand = float(d)
        except (ValueError, IndexError):
            continue
        week_to_demand[week] = demand

    missing = [w for w in range(WEEK_START, WEEK_END + 1) if w not in week_to_demand]
    if missing:
        raise ValueError(f"Missing demand values for weeks: {missing}")

    return [(w, week_to_demand[w]) for w in range(WEEK_START, WEEK_END + 1)]


def choose_days(calc_start: float, demand: float) -> int:
    start_past_due = max(0.0, calc_start)
    if start_past_due > 0.01:
        for days in (5, 6):
            if calc_start + demand - (RATE_PER_DAY * days) <= 0.0:
                return days
        return 6

    if demand <= 112.0:
        return 4
    return 5


def build_plan() -> List[Tuple[int, int, float, float, float, float, float]]:
    demand_data = load_weekly_demand(INPUT_CSV)

    week5_demand = demand_data[0][1]
    calc_start = INITIAL_WEEK5_TOTAL - week5_demand

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
        "After catch-up, hold 4 days when weekly demand is 112 hours or lower."
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
