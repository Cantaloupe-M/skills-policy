#!/usr/bin/env python3
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openpyxl import Workbook, load_workbook


def normalize_text(value: Any) -> str:
    return str(value or '').strip().upper()


def to_number(value: Any) -> float:
    if value in (None, ''):
        return 0.0
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(',', '').strip()
    return float(text) if text else 0.0


def parse_date(value: Any) -> date | None:
    if value in (None, ''):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def to_iso(value: date | None) -> str:
    return value.isoformat() if value else ''


def diff_days(start: date, end: date) -> int:
    return (end - start).days


def add_days(start: date, days: int) -> date:
    return start + timedelta(days=days)


def round_to(value: float, decimals: int = 4) -> float:
    factor = 10 ** decimals
    return round(value * factor) / factor


def main():
    input_root = Path(sys.argv[1])
    output_root = Path(sys.argv[2])
    inv_wb = load_workbook(input_root / 'Produce_Lane_Inventory.xlsx', data_only=True)
    arr_wb = load_workbook(input_root / 'Produce_Arrivals.xlsx', data_only=True)
    stock_ws = inv_wb['Lane Snapshot']
    arr_ws = arr_wb['Arrival Board']

    as_of = parse_date(stock_ws['B1'].value)
    horizon = parse_date(stock_ws['D1'].value)
    planning_days = diff_days(as_of, horizon)
    pallet_size = 54.0

    inventory = []
    current_lane = ''
    r = 3
    while r <= stock_ws.max_row:
        label = str(stock_ws.cell(row=r, column=1).value or '').strip()
        if label.upper().startswith('LANE:'):
            current_lane = label.split(':', 1)[1].strip().upper()
            r += 2
            continue
        sku = normalize_text(stock_ws.cell(row=r, column=1).value)
        if current_lane and sku and sku != 'SKU':
            units = to_number(stock_ws.cell(row=r, column=2).value)
            rate = to_number(stock_ws.cell(row=r, column=3).value)
            inventory.append((current_lane, sku, units, rate))
        r += 1

    inbound_by_key: Dict[Tuple[str, str], List[Tuple[date, float]]] = {}
    valid_statuses = {'READY', 'DOCKED'}
    for r in range(2, arr_ws.max_row + 1):
        lane = normalize_text(arr_ws.cell(row=r, column=1).value)
        sku = normalize_text(arr_ws.cell(row=r, column=2).value)
        eta = parse_date(arr_ws.cell(row=r, column=3).value)
        units = to_number(arr_ws.cell(row=r, column=4).value)
        status = normalize_text(arr_ws.cell(row=r, column=5).value)
        if not lane or not sku or eta is None or status not in valid_statuses:
            continue
        inbound_by_key.setdefault((lane, sku), []).append((eta, units))

    detail_rows = []
    action_rows = []
    for lane, sku, units, rate in inventory:
        inbound = inbound_by_key.get((lane, sku), [])
        inbound_in_horizon = sum(c for d, c in inbound if d <= horizon)
        earliest = min((d for d, c in inbound if d <= horizon), default=None)
        current_doh = units / rate if rate > 0 else None
        proj_oos = add_days(as_of, int(current_doh)) if current_doh is not None else None
        delivered_doh = (units + inbound_in_horizon) / rate if rate > 0 else None
        remaining_demand = rate * planning_days
        additional = max(0.0, remaining_demand - units - inbound_in_horizon) if rate > 0 else 0.0
        pallets = math.ceil(additional / pallet_size) if additional > 0 else 0
        req_date = proj_oos if pallets > 0 else None
        earlier = pallets > 0 and (earliest is None or (req_date and req_date < earliest))
        detail_rows.append([
            lane, sku, units, rate,
            round_to(current_doh) if current_doh is not None else '',
            to_iso(proj_oos),
            inbound_in_horizon,
            round_to(delivered_doh) if delivered_doh is not None else '',
            round_to(remaining_demand),
            round_to(additional),
            pallets,
            to_iso(req_date),
            earlier,
        ])
        if pallets > 0:
            action_rows.append([lane, sku, to_iso(req_date), pallets, round_to(additional), earlier])

    out_wb = Workbook()
    detail_ws = out_wb.active
    detail_ws.title = 'Lane_Coverage'
    detail_ws['A1'] = 'Field'
    detail_ws['B1'] = 'Value'
    detail_ws['A2'] = 'AsOfDate'
    detail_ws['B2'] = to_iso(as_of)
    detail_ws['A3'] = 'HorizonEnd'
    detail_ws['B3'] = to_iso(horizon)
    detail_ws['A4'] = 'PlanningDays'
    detail_ws['B4'] = planning_days
    headers = ['Lane', 'SKU', 'Cases_On_Hand', 'Daily_Pull_Cases_Per_Day', 'Current_Days_On_Hand', 'Projected_OOS_Date', 'Inbound_Cases_By_Horizon', 'Delivered_Days_On_Hand', 'Remaining_Demand_Cases', 'Additional_Cases_Needed', 'Pallets_Required', 'Required_Delivery_Date', 'Earlier_Delivery_Required']
    for i, h in enumerate(headers, 1):
        detail_ws.cell(row=6, column=i, value=h)
    for r, row in enumerate(detail_rows, 7):
        for c, val in enumerate(row, 1):
            detail_ws.cell(row=r, column=c, value=val)

    action_ws = out_wb.create_sheet('Restock_Actions')
    action_headers = ['Lane', 'SKU', 'Required_Delivery_Date', 'Pallets_Required', 'Additional_Cases_Needed', 'Earlier_Delivery_Required']
    for i, h in enumerate(action_headers, 1):
        action_ws.cell(row=1, column=i, value=h)
    for r, row in enumerate(action_rows, 2):
        for c, val in enumerate(row, 1):
            action_ws.cell(row=r, column=c, value=val)

    output_file = output_root / 'produce_lane_restock_gap.xlsx'
    out_wb.save(output_file)

    print('Wrote', output_file)


if __name__ == '__main__':
    main()
