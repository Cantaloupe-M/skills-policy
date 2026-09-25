#!/bin/bash
set -euo pipefail

cat > /tmp/build_plan.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import Workbook

INPUT_JSON = Path("/root/chemical_demand.json")
OUTPUT_XLSX = Path("/root/chemical_schedule_plan.xlsx")
OUTPUT_SUMMARY = Path("/root/chemical_schedule_summary.txt")

PHASE_START = 10
PHASE_END = 58
INITIAL_PHASE10_TOTAL = 1453.06
RATE_PER_DAY = 40.0


def load_phase_demand(path: Path) -> List[Tuple[int, float]]:
    """
    Read the JSON file.
    JSON structure: list of objects:
      {"week": N, "data": {"demand_per_week": float or null}, "priority": "HIGH"|"MED"|"LOW"|"NORMAL"}

    - Some weeks appear more than once (duplicate entries)
    - Some entries have null demand_per_week (missing values)
    - Use the FIRST valid (non-null) occurrence of each week
    """
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    phase_to_demand: Dict[int, float] = {}
    for rec in records:
        week = int(rec["week"])
        demand = rec["data"]["demand_per_week"]

        # Skip if week already seen (keep first occurrence)
        if week in phase_to_demand:
            continue
        # Skip null demand values
        if demand is None:
            continue

        phase_to_demand[week] = float(demand)

    missing = [p for p in range(PHASE_START, PHASE_END + 1) if p not in phase_to_demand]
    if missing:
        raise ValueError(f"Missing demand values for phases: {missing}")

    return [(p, phase_to_demand[p]) for p in range(PHASE_START, PHASE_END + 1)]


def choose_days(calc_start: float, demand: float) -> int:
    start_past_due = max(0.0, calc_start)
    if start_past_due > 0.01:
        for days in (5, 6):
            if calc_start + demand - (RATE_PER_DAY * days) <= 0.0:
                return days
        return 6

    if demand <= 160.0:
        return 4
    return 5


def build_plan() -> List[Tuple[int, int, float, float, float, float, float]]:
    demand_data = load_phase_demand(INPUT_JSON)

    phase10_demand = demand_data[0][1]
    calc_start = INITIAL_PHASE10_TOTAL - phase10_demand

    rows: List[Tuple[int, int, float, float, float, float, float]] = []
    for phase, demand in demand_data:
        days = choose_days(calc_start, demand)
        capacity = RATE_PER_DAY * days
        start_past_due = max(0.0, calc_start)
        end_backlog_buffer = calc_start + demand - capacity
        overtime = 10.0 * max(0, days - 4)

        rows.append(
            (
                phase,
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
        "Phase",
        "Days Worked",
        "Scheduled Demand (Std Hrs)",
        "Weekly Capacity (Std Hrs)",
        "Start of Phase Past Due (Std Hrs)",
        "End of Phase Backlog/Buffer (Std Hrs)",
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
    first_phase_5 = next((phase for phase, days, *_ in rows if days == 5), None)
    first_phase_4 = next((phase for phase, days, *_ in rows if days == 4), None)

    fp5 = str(first_phase_5) if first_phase_5 is not None else "N/A"
    fp4 = str(first_phase_4) if first_phase_4 is not None else "N/A"

    summary = (
        f"Shift to 5 days in Phase {fp5} and to 4 days in Phase {fp4}. "
        "Before catch-up, use 5 or 6 days based on backlog clearance. "
        "After catch-up, hold 4 days when weekly demand is 160 hours or lower."
    )

    lines = [
        f"First_Week_5_Days: {fp5}",
        f"First_Week_4_Days: {fp4}",
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
