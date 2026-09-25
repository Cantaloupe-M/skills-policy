#!/bin/bash
set -euo pipefail

cat > /tmp/build_plan.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from openpyxl import Workbook, load_workbook

INPUT_XLSX = Path("/root/hvac_demand_sheet.xlsx")
OUTPUT_XLSX = Path("/root/hvac_schedule_plan.xlsx")
OUTPUT_EXISTING = Path("/root/hvac_existing_plan.xlsx")
OUTPUT_SUMMARY = Path("/root/hvac_schedule_summary.txt")

PHASE_START = 8
PHASE_END = 56
INITIAL_PHASE8_TOTAL = 1138.66
RATE_PER_DAY = 35.0


def _clean_label(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def load_phase_demand(path: Path) -> List[Tuple[int, float]]:
    wb = load_workbook(path, data_only=True)
    ws = wb["Install"] if "Install" in wb.sheetnames else wb.active

    # The workbook stores the plan inputs as a two-column table.
    phase_to_demand: Dict[int, float] = {}
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=2, values_only=True):
        if not row:
            continue
        phase_val = row[0]
        demand_val = row[1] if len(row) > 1 else None
        if phase_val is None or demand_val is None:
            continue
        try:
            phase = int(round(float(phase_val)))
            demand = float(demand_val)
        except (TypeError, ValueError):
            continue
        phase_to_demand[phase] = demand

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

    if demand <= 140.0:
        return 4
    return 5


def build_plan() -> List[Tuple[int, int, float, float, float, float, float]]:
    demand_data = load_phase_demand(INPUT_XLSX)

    phase8_demand = demand_data[0][1]
    calc_start = INITIAL_PHASE8_TOTAL - phase8_demand

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


def save_workbook(rows: List[Tuple[int, int, float, float, float, float, float]], path: Path) -> None:
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

    wb.save(path)


def save_summary(rows: List[Tuple[int, int, float, float, float, float, float]]) -> None:
    first_phase_5 = next((phase for phase, days, *_ in rows if days == 5), None)
    first_phase_4 = next((phase for phase, days, *_ in rows if days == 4), None)

    fp5 = str(first_phase_5) if first_phase_5 is not None else "N/A"
    fp4 = str(first_phase_4) if first_phase_4 is not None else "N/A"

    summary = (
        f"Shift to 5 days in Phase {fp5} and to 4 days in Phase {fp4}. "
        "Before catch-up, use 5 or 6 days based on backlog clearance. "
        "After catch-up, hold 4 days when weekly demand is 140 hours or lower."
    )

    lines = [
        f"First_Week_5_Days: {fp5}",
        f"First_Week_4_Days: {fp4}",
        f"Summary: {summary}",
    ]
    OUTPUT_SUMMARY.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = build_plan()
    # Write to existing plan file (overwrite)
    save_workbook(rows, OUTPUT_EXISTING)
    # Also write copy to the main output path
    save_workbook(rows, OUTPUT_XLSX)
    save_summary(rows)
    print(f"Wrote {OUTPUT_EXISTING}")
    print(f"Wrote {OUTPUT_XLSX}")
    print(f"Wrote {OUTPUT_SUMMARY}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /tmp/build_plan.py
