#!/usr/bin/env python3
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


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


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return normalize_text(value) in ('TRUE', 'T', 'YES', 'Y', '1')


def round_to(value: float, decimals: int = 4) -> float:
    factor = 10 ** decimals
    return round(value * factor) / factor


def assert_approx(actual: Any, expected: float, tolerance: float, msg: str):
    a = to_number(actual)
    assert abs(a - expected) <= tolerance, f'{msg}: actual={a}, expected={expected}'


def compute_expected(input_root: Path):

    stock_wb = load_workbook(input_root / 'Beauty_Zone_Stock.xlsx', data_only=True)
    feed_wb = load_workbook(input_root / 'Beauty_Mixed_Feed.xlsx', data_only=True)
    alias_wb = load_workbook(input_root / 'Beauty_Zone_Alias_Key.xlsx', data_only=True)
    stock_ws = stock_wb['Zone Snapshot']
    feed_ws = feed_wb['Zone Feed']
    alias_ws = alias_wb['Alias Map']
    as_of = parse_date(stock_ws['B1'].value)
    horizon = parse_date(stock_ws['D1'].value)
    planning_days = diff_days(as_of, horizon)
    inventory = []
    for r in range(4, stock_ws.max_row + 1):
        zone = normalize_text(stock_ws.cell(row=r, column=1).value)
        sku = normalize_text(stock_ws.cell(row=r, column=2).value)
        if not zone or not sku:
            continue
        inventory.append((zone, sku, to_number(stock_ws.cell(row=r, column=3).value), to_number(stock_ws.cell(row=r, column=4).value)))
    alias_map = {}
    for r in range(2, alias_ws.max_row + 1):
        alias = normalize_text(alias_ws.cell(row=r, column=1).value)
        zone = normalize_text(alias_ws.cell(row=r, column=2).value)
        if alias and zone:
            alias_map[alias] = zone
    latest = {}
    for r in range(2, feed_ws.max_row + 1):
        rtype = normalize_text(feed_ws.cell(row=r, column=1).value)
        ref = normalize_text(feed_ws.cell(row=r, column=2).value)
        rev = int(to_number(feed_ws.cell(row=r, column=3).value))
        alias = normalize_text(feed_ws.cell(row=r, column=4).value)
        sku = normalize_text(feed_ws.cell(row=r, column=5).value)
        eta = parse_date(feed_ws.cell(row=r, column=6).value)
        units = to_number(feed_ws.cell(row=r, column=7).value)
        state = normalize_text(feed_ws.cell(row=r, column=8).value)
        if rtype != 'DELIVERY' or not ref:
            continue
        prev = latest.get(ref)
        if prev is None or rev > prev[0]:
            latest[ref] = (rev, alias, sku, eta, units, state)
    inbound_by_key = {}
    valid = {'RELEASED', 'STAGED'}
    for rev, alias, sku, eta, units, state in latest.values():
        zone = alias_map.get(alias, '')
        if not zone or not sku or eta is None or state not in valid:
            continue
        inbound_by_key.setdefault((zone, sku), []).append((eta, units))
    detail_map = {}
    detail_order = []
    action_map = {}
    action_keys = set()
    for zone, sku, units, rate in inventory:
        key = (zone, sku)
        detail_order.append(key)
        inbound = inbound_by_key.get(key, [])
        inbound_in_horizon = sum(c for d, c in inbound if d <= horizon)
        earliest = min((d for d, c in inbound if d <= horizon), default=None)
        current_doh = units / rate if rate > 0 else None
        proj_oos = add_days(as_of, int(current_doh)) if current_doh is not None else None
        delivered_doh = (units + inbound_in_horizon) / rate if rate > 0 else None
        remaining = rate * planning_days
        additional = max(0.0, remaining - units - inbound_in_horizon) if rate > 0 else 0.0
        pallets = math.ceil(additional / 36.0) if additional > 0 else 0
        req = proj_oos if pallets > 0 else None
        earlier = pallets > 0 and (earliest is None or (req and req < earliest))
        detail_map[key] = {'Zone': zone, 'SKU': sku, 'Units_On_Hand': units, 'Daily_Demand_Units_Per_Day': rate, 'Current_Days_On_Hand': round_to(current_doh) if current_doh is not None else '', 'Projected_OOS_Date': to_iso(proj_oos), 'Inbound_Units_By_Horizon': inbound_in_horizon, 'Delivered_Days_On_Hand': round_to(delivered_doh) if delivered_doh is not None else '', 'Remaining_Demand_Units': round_to(remaining), 'Additional_Units_Needed': round_to(additional), 'Pallets_Required': pallets, 'Required_Delivery_Date': to_iso(req), 'Earlier_Delivery_Required': earlier}
        if pallets > 0:
            action_keys.add(key)
            action_map[key] = {'Zone': zone, 'SKU': sku, 'Required_Delivery_Date': to_iso(req), 'Pallets_Required': pallets, 'Additional_Units_Needed': round_to(additional), 'Earlier_Delivery_Required': earlier}
    return {'as_of': as_of, 'horizon': horizon, 'planning_days': planning_days, 'detail_order': detail_order, 'detail_map': detail_map, 'action_map': action_map, 'action_keys': action_keys}



def read_actual(output_file: Path):
    wb = load_workbook(output_file, data_only=True)
    assert set(wb.sheetnames) == set(['Zone_Coverage', 'Dispatch_Gap_List']), f'Sheet names mismatch: {wb.sheetnames}'
    detail_ws = wb['Zone_Coverage']
    action_ws = wb['Dispatch_Gap_List']

    assert detail_ws['A1'].value.strip().lower() == 'field'
    assert detail_ws['B1'].value.strip().lower() == 'value'
    as_of = parse_date(detail_ws['B2'].value)
    horizon = parse_date(detail_ws['B3'].value)
    planning_days = int(to_number(detail_ws['B4'].value))
    header = [detail_ws.cell(row=6, column=c).value for c in range(1, 13 + 1)]
    assert set(header) == set(['Zone', 'SKU', 'Units_On_Hand', 'Daily_Demand_Units_Per_Day', 'Current_Days_On_Hand', 'Projected_OOS_Date', 'Inbound_Units_By_Horizon', 'Delivered_Days_On_Hand', 'Remaining_Demand_Units', 'Additional_Units_Needed', 'Pallets_Required', 'Required_Delivery_Date', 'Earlier_Delivery_Required']), f'Detail header mismatch: {header}'
    detail_order = []
    detail_map = {}
    for r in range(7, detail_ws.max_row + 1):
        row = [detail_ws.cell(row=r, column=c).value for c in range(1, 13 + 1)]
        key = tuple(normalize_text(v) for v in row[:2])
        if not all(key):
            continue
        detail_order.append(key)
        detail_map[key] = dict(zip(['Zone', 'SKU', 'Units_On_Hand', 'Daily_Demand_Units_Per_Day', 'Current_Days_On_Hand', 'Projected_OOS_Date', 'Inbound_Units_By_Horizon', 'Delivered_Days_On_Hand', 'Remaining_Demand_Units', 'Additional_Units_Needed', 'Pallets_Required', 'Required_Delivery_Date', 'Earlier_Delivery_Required'], row))
    action_header = [action_ws.cell(row=1, column=c).value for c in range(1, 6 + 1)]
    assert set(action_header) == set(['Zone', 'SKU', 'Required_Delivery_Date', 'Pallets_Required', 'Additional_Units_Needed', 'Earlier_Delivery_Required']), f'Action header mismatch: {action_header}'
    action_order = []
    action_map = {}
    for r in range(2, action_ws.max_row + 1):
        row = [action_ws.cell(row=r, column=c).value for c in range(1, 6 + 1)]
        key = tuple(normalize_text(v) for v in row[:2])
        if not all(key):
            continue
        action_order.append(key)
        action_map[key] = dict(zip(['Zone', 'SKU', 'Required_Delivery_Date', 'Pallets_Required', 'Additional_Units_Needed', 'Earlier_Delivery_Required'], row))
    return {'as_of': as_of, 'horizon': horizon, 'planning_days': planning_days, 'detail_order': detail_order, 'detail_map': detail_map, 'action_order': action_order, 'action_map': action_map}


def compare(expected: dict, actual: dict):
    assert actual['as_of'] == expected['as_of']
    assert actual['horizon'] == expected['horizon']
    assert actual['planning_days'] == expected['planning_days']
    assert set(actual['detail_order']) == set(expected['detail_order'])
    for key in expected['detail_order']:
        erow = expected['detail_map'][key]
        arow = actual['detail_map'][key]
        for field in ['Zone', 'SKU', 'Units_On_Hand', 'Daily_Demand_Units_Per_Day', 'Current_Days_On_Hand', 'Projected_OOS_Date', 'Inbound_Units_By_Horizon', 'Delivered_Days_On_Hand', 'Remaining_Demand_Units', 'Additional_Units_Needed', 'Pallets_Required', 'Required_Delivery_Date', 'Earlier_Delivery_Required']:
            ev = erow[field]
            av = arow[field]
            if field in ['Units_On_Hand', 'Daily_Demand_Units_Per_Day', 'Current_Days_On_Hand', 'Inbound_Units_By_Horizon', 'Delivered_Days_On_Hand', 'Remaining_Demand_Units', 'Additional_Units_Needed', 'Pallets_Required']:
                assert_approx(av, ev, 1e-4, f'detail {key} {field}')
            elif field in ['Projected_OOS_Date', 'Required_Delivery_Date']:
                assert normalize_text(av) == normalize_text(ev), f'detail {key} {field}: {av} vs {ev}'
            elif field in ['Earlier_Delivery_Required']:
                assert to_bool(av) == bool(ev), f'detail {key} {field}: {av} vs {ev}'
            else:
                assert normalize_text(av) == normalize_text(ev), f'detail {key} {field}: {av} vs {ev}'
    expected_action_order = [k for k in expected['detail_order'] if k in expected['action_keys']]
    assert set(actual['action_order']) == set(expected_action_order)
    for key in expected_action_order:
        erow = expected['action_map'][key]
        arow = actual['action_map'][key]
        for field in ['Zone', 'SKU', 'Required_Delivery_Date', 'Pallets_Required', 'Additional_Units_Needed', 'Earlier_Delivery_Required']:
            ev = erow[field]
            av = arow[field]
            if field in ['Units_On_Hand', 'Daily_Demand_Units_Per_Day', 'Current_Days_On_Hand', 'Inbound_Units_By_Horizon', 'Delivered_Days_On_Hand', 'Remaining_Demand_Units', 'Additional_Units_Needed', 'Pallets_Required']:
                assert_approx(av, ev, 1e-4, f'action {key} {field}')
            elif field in ['Projected_OOS_Date', 'Required_Delivery_Date']:
                assert normalize_text(av) == normalize_text(ev), f'action {key} {field}: {av} vs {ev}'
            elif field in ['Earlier_Delivery_Required']:
                assert to_bool(av) == bool(ev), f'action {key} {field}: {av} vs {ev}'
            else:
                assert normalize_text(av) == normalize_text(ev), f'action {key} {field}: {av} vs {ev}'


def main():
    in_harness = Path('/tests').exists() and Path('/root').exists()
    task_dir = Path(__file__).resolve().parents[1]
    input_root = Path('/root') if in_harness else (task_dir / 'environment')
    output_file = Path('/root/beauty_zone_alias_gap.xlsx') if in_harness else (task_dir / 'beauty_zone_alias_gap.xlsx')
    assert output_file.exists(), f'Missing output file: {output_file}'
    expected = compute_expected(input_root)
    actual = read_actual(output_file)
    compare(expected, actual)
    print('All checks passed.')


if __name__ == '__main__':
    main()
