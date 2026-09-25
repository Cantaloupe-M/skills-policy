"""
Shared helper for extracting series, deflating, and computing HP-filter correlations.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd


def normalize(text):
    """Normalize label for robust comparison."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def locate_input(filename):
    """Find input file in task root or /root."""
    task_root = Path(__file__).resolve().parents[2]
    candidates = [Path("/root") / filename, task_root / "environment" / filename]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not locate input file: {filename}")


def locate_output():
    """Locate answer.txt output path."""
    root = Path("/root")
    if root.exists():
        return root / "answer.txt"
    return Path(__file__).resolve().parents[2] / "answer.txt"


def write_answer(value):
    """Write rounded correlation to answer.txt."""
    locate_output().write_text(f"{value:.5f}", encoding="utf-8")


def _hp_cycle(values, lamb=100):
    """HP filter returning cyclical component."""
    values = np.asarray(values, dtype=float)
    try:
        from statsmodels.tsa.filters.hp_filter import hpfilter
        cycle, _ = hpfilter(values, lamb=lamb)
        return np.asarray(cycle, dtype=float)
    except Exception:
        n = len(values)
        if n < 3:
            raise ValueError("Need at least 3 observations for HP filter")
        d = np.zeros((n - 2, n), dtype=float)
        for i in range(n - 2):
            d[i, i : i + 3] = [1.0, -2.0, 1.0]
        trend = np.linalg.solve(np.eye(n) + lamb * (d.T @ d), values)
        return values - trend


def cycle_correlation_from_nominal(series_a, series_b, deflator_a, deflator_b=None):
    """Core workflow: deflate → log → HP → correlation."""
    if deflator_b is None:
        deflator_b = deflator_a
    years = sorted(set(series_a) & set(series_b) & set(deflator_a) & set(deflator_b))
    if len(years) < 8:
        raise ValueError("Too few aligned observations after merging.")
    real_a = np.array([float(series_a[y]) / float(deflator_a[y]) for y in years])
    real_b = np.array([float(series_b[y]) / float(deflator_b[y]) for y in years])
    cycle_a = _hp_cycle(np.log(real_a), lamb=100)
    cycle_b = _hp_cycle(np.log(real_b), lamb=100)
    return float(np.corrcoef(cycle_a, cycle_b)[0, 1])


def read_index_columns(workbook_name, sheet_name):
    """Read price index table with year column and value columns."""
    df = pd.read_excel(locate_input(workbook_name), sheet_name=sheet_name)
    year_col = None
    for col in df.columns:
        if normalize(col) in {"year", "calendaryear"}:
            year_col = col
            break
    if year_col is None:
        raise ValueError(f"Could not find year column in {workbook_name}:{sheet_name}")

    df = df.copy()
    df[year_col] = pd.to_numeric(df[year_col], errors="coerce")

    out = {}
    for col in df.columns:
        if col == year_col:
            continue
        values = {}
        numeric_vals = pd.to_numeric(df[col], errors="coerce")
        for yr, val in zip(df[year_col], numeric_vals):
            if pd.notna(yr) and pd.notna(val):
                values[int(yr)] = float(val)
        out[str(col)] = values
    return out


def _find_row_with_label(df, label):
    target = normalize(label)
    for idx, row in df.iterrows():
        cells = [normalize(c) for c in row.tolist() if pd.notna(c)]
        if target in cells:
            return idx
    raise ValueError(f"Could not find row containing label: {label}")


def extract_canonical_table(workbook_name, sheet_name, value_column, start_year, current_year):
    """
    Extract annual series from 'canonical' long table.
    Handles annual rows like '1994.' and quarterly block for current_year.
    """
    df = pd.read_excel(locate_input(workbook_name), sheet_name=sheet_name, header=None)
    header_idx = _find_row_with_label(df, value_column)
    header = [str(c).strip() if pd.notna(c) else "" for c in df.iloc[header_idx].tolist()]
    label_col = 0
    value_idx = None
    for i, cell in enumerate(header):
        if normalize(cell) == normalize(value_column):
            value_idx = i
            break
    if value_idx is None:
        raise ValueError(f"Could not find value column '{value_column}'")

    annual = {}
    current_values = []
    in_current_block = False

    for row in df.iloc[header_idx + 1 :].itertuples(index=False):
        label = str(row[label_col]).strip() if pd.notna(row[label_col]) else ""
        value = pd.to_numeric(row[value_idx], errors="coerce")
        if re.fullmatch(r"\d{4}\.", label):
            yr = int(label[:-1])
            if start_year <= yr < current_year and pd.notna(value):
                annual[yr] = float(value)
            in_current_block = False
        elif str(current_year) in label and ("I" in label or "Q1" in label.upper()):
            if pd.notna(value):
                current_values = [float(value)]
                in_current_block = True
        elif in_current_block and normalize(label) in {"ii", "iii", "iv", "q2", "q3", "q4"}:
            if pd.notna(value):
                current_values.append(float(value))
        elif in_current_block:
            in_current_block = False

    if current_values:
        annual[current_year] = sum(current_values) / len(current_values)

    return {yr: annual[yr] for yr in sorted(annual) if start_year <= yr <= current_year}


def extract_long_panel(workbook_name, annual_sheet, update_sheet, series_label, start_year, current_year, annual_status, update_status):
    """
    Extract series from long panel with status filtering.
    Used for structural tasks.
    """
    annual_df = pd.read_excel(locate_input(workbook_name), sheet_name=annual_sheet)
    update_df = pd.read_excel(locate_input(workbook_name), sheet_name=update_sheet)
    target = normalize(series_label)

    annual_subset = annual_df[annual_df["series_label"].map(normalize) == target].copy()
    annual_subset = annual_subset[annual_subset["period_kind"].astype(str).str.lower() == "annual"]
    annual_subset = annual_subset[annual_subset["release_status"].astype(str).str.lower() == annual_status.lower()]

    out = {}
    for _, r in annual_subset.iterrows():
        match = re.search(r"(19|20)\d{2}", str(r["period_label"]))
        if not match:
            continue
        yr = int(match.group())
        val = pd.to_numeric(r["amount"], errors="coerce")
        if start_year <= yr < current_year and pd.notna(val):
            out[yr] = float(val)

    update_subset = update_df[update_df["series_label"].map(normalize) == target].copy()
    update_subset = update_subset[update_subset["release_status"].astype(str).str.lower() == update_status.lower()]
    vals = []
    for v in pd.to_numeric(
        update_subset.loc[
            update_subset["month"].astype(str).str.contains(str(current_year)),
            "amount",
        ],
        errors="coerce",
    ).dropna():
        vals.append(float(v))
    if vals:
        out[current_year] = sum(vals) / len(vals)

    return {yr: out[yr] for yr in sorted(out) if start_year <= yr <= current_year}


def extract_catalog_series(history_workbook, current_workbook, catalog_csv, requested_series, current_year):
    """
    Extract series using catalog mapping (code-based).
    Returns (year->value dict, deflator_column_name).
    """
    catalog = pd.read_csv(locate_input(catalog_csv))
    match = catalog[catalog["requested_series"] == requested_series]
    if match.empty:
        raise ValueError(f"Requested series not found in catalog: {requested_series}")
    row = match.iloc[0]

    history_raw = pd.read_excel(locate_input(history_workbook), sheet_name=row["history_sheet"], header=None)
    header_idx = _find_row_with_label(history_raw, "calendar_year")
    header = [str(c).strip() if pd.notna(c) else "" for c in history_raw.iloc[header_idx].tolist()]
    history_df = history_raw.iloc[header_idx + 1 :].copy()
    history_df.columns = header

    year_col = None
    for col in history_df.columns:
        if normalize(col) == "calendaryear":
            year_col = col
            break
    if year_col is None:
        raise ValueError("Could not find calendar year column in history workbook")

    output = {}
    for _, r in history_df.iterrows():
        yr = pd.to_numeric(r[year_col], errors="coerce")
        val = pd.to_numeric(r[row["history_code"]], errors="coerce")
        if pd.notna(yr) and pd.notna(val) and int(yr) < current_year:
            output[int(yr)] = float(val)

    current_df = pd.read_excel(locate_input(current_workbook), sheet_name=row["current_sheet"])
    current_subset = current_df[current_df["series_code"] == row["current_code"]].copy()
    current_subset = current_subset[current_subset["version"].astype(str).str.lower() == "revised"]
    vals = []
    for v in pd.to_numeric(
        current_subset.loc[
            current_subset["subperiod"].astype(str).str.contains(str(current_year)),
            "value",
        ],
        errors="coerce",
    ).dropna():
        vals.append(float(v))
    if vals:
        output[current_year] = sum(vals) / len(vals)

    return (
        {yr: output[yr] for yr in sorted(output)},
        row["deflator_column"],
    )
