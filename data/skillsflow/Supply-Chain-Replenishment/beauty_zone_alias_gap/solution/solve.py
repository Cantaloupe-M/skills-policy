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
    stock_wb = load_workbook(input_root / 'Beauty_Zone_Stock.xlsx', data_only=True)
    feed_wb = load_workbook(input_root / 'Beauty_Mixed_Feed.xlsx', data_only=True)
    alias_wb = load_workbook(input_root / 'Beauty_Zone_Alias_Key.xlsx', data_only=True)
    stock_ws = stock_wb['Zone Snapshot']
    feed_ws = feed_wb['Zone Feed']
    alias_ws = alias_wb['Alias Map']

    as_of = parse_date(stock_ws['B1'].value)
    horizon = parse_date(stock_ws['D1'].value)
    planning_days = diff_days(as_of, horizon)
    pallet_size = 36.0

    inventory = []
    for r in range(4, stock_ws.max_row + 1):
        zone = normalize_text(stock_ws.cell(row=r, column=1).value)
        sku = normalize_text(stock_ws.cell(row=r, column=2).value)
        if not zone or not sku:
            continue
        units = to_number(stock_ws.cell(row=r, column=3).value)
        rate = to_number(stock_ws.cell(row=r, column=4).value)
        inventory.append((zone, sku, units, rate))

    alias_map: Dict[str, str] = {}
    for r in range(2, alias_ws.max_row + 1):
        alias = normalize_text(alias_ws.cell(row=r, column=1).value)
        zone = normalize_text(alias_ws.cell(row=r, column=2).value)
        if alias and zone:
            alias_map[alias] = zone

    latest_by_ref: Dict[str, Tuple[int, str, str, date | None, float, str]] = {}
    for r in range(2, feed_ws.max_row + 1):
        record_type = normalize_text(feed_ws.cell(row=r, column=1).value)
        ref = normalize_text(feed_ws.cell(row=r, column=2).value)
        rev = int(to_number(feed_ws.cell(row=r, column=3).value))
        alias = normalize_text(feed_ws.cell(row=r, column=4).value)
        sku = normalize_text(feed_ws.cell(row=r, column=5).value)
        eta = parse_date(feed_ws.cell(row=r, column=6).value)
        units = to_number(feed_ws.cell(row=r, column=7).value)
        state = normalize_text(feed_ws.cell(row=r, column=8).value)
        if record_type != 'DELIVERY' or not ref:
            continue
        prev = latest_by_ref.get(ref)
        if prev is None or rev > prev[0]:
            latest_by_ref[ref] = (rev, alias, sku, eta, units, state)

    inbound_by_key: Dict[Tuple[str, str], List[Tuple[date, float]]] = {}
    valid_states = {'RELEASED', 'STAGED'}
    for rev, alias, sku, eta, units, state in latest_by_ref.values():
        zone = alias_map.get(alias, '')
        if not zone or not sku or eta is None or state not in valid_states:
            continue
        inbound_by_key.setdefault((zone, sku), []).append((eta, units))

    detail_rows = []
    action_rows = []
    for zone, sku, units, rate in inventory:
        inbound = inbound_by_key.get((zone, sku), [])
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
            zone, sku, units, rate,
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
            action_rows.append([zone, sku, to_iso(req_date), pallets, round_to(additional), earlier])

    out_wb = Workbook()
    detail_ws = out_wb.active
    detail_ws.title = 'Zone_Coverage'
    detail_ws['A1'] = 'Field'
    detail_ws['B1'] = 'Value'
    detail_ws['A2'] = 'AsOfDate'
    detail_ws['B2'] = to_iso(as_of)
    detail_ws['A3'] = 'HorizonEnd'
    detail_ws['B3'] = to_iso(horizon)
    detail_ws['A4'] = 'PlanningDays'
    detail_ws['B4'] = planning_days
    headers = ['Zone', 'SKU', 'Units_On_Hand', 'Daily_Demand_Units_Per_Day', 'Current_Days_On_Hand', 'Projected_OOS_Date', 'Inbound_Units_By_Horizon', 'Delivered_Days_On_Hand', 'Remaining_Demand_Units', 'Additional_Units_Needed', 'Pallets_Required', 'Required_Delivery_Date', 'Earlier_Delivery_Required']
    for i, h in enumerate(headers, 1):
        detail_ws.cell(row=6, column=i, value=h)
    for r, row in enumerate(detail_rows, 7):
        for c, val in enumerate(row, 1):
            detail_ws.cell(row=r, column=c, value=val)

    action_ws = out_wb.create_sheet('Dispatch_Gap_List')
    action_headers = ['Zone', 'SKU', 'Required_Delivery_Date', 'Pallets_Required', 'Additional_Units_Needed', 'Earlier_Delivery_Required']
    for i, h in enumerate(action_headers, 1):
        action_ws.cell(row=1, column=i, value=h)
    for r, row in enumerate(action_rows, 2):
        for c, val in enumerate(row, 1):
            action_ws.cell(row=r, column=c, value=val)

    output_file = output_root / 'beauty_zone_alias_gap.xlsx'
    out_wb.save(output_file)

    print('Wrote', output_file)


if __name__ == '__main__':
    main()
