"""
Shared helper for extracting series, deflating, and computing HP-filter correlations.
Used by Tasks 5-8 in the extended family.
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd


def normalize(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def locate_input(filename):
    task_root = Path(__file__).resolve().parents[2]
    candidates = [Path("/root") / filename, task_root / "environment" / filename]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not locate input file: {filename}")


def locate_output():
    root = Path("/root")
    if root.exists():
        return root / "answer.txt"
    return Path(__file__).resolve().parents[2] / "answer.txt"


def write_answer(value):
    locate_output().write_text(f"{value:.5f}", encoding="utf-8")


def _hp_cycle(values, lamb=100):
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


def extract_wide_matrix(workbook_name, sheet_name, requested_series, series_column, status_column, keep_status, start_year, current_year):
    df = pd.read_excel(locate_input(workbook_name), sheet_name=sheet_name)
    target = normalize(requested_series)
    subset = df[(df[series_column].map(normalize) == target) & (df[status_column].astype(str).str.lower() == keep_status.lower())]
    if subset.empty:
        raise ValueError(f"Could not find requested series '{requested_series}' in wide matrix")
    row = subset.iloc[0]
    out = {}
    for col in df.columns:
        match = re.search(r"((?:19|20)\d{2})", str(col))
        if not match:
            continue
        yr = int(match.group(1))
        if start_year <= yr < current_year:
            val = pd.to_numeric(row[col], errors="coerce")
            if pd.notna(val):
                out[yr] = float(val)
    return out


def load_table(filename, sheet_name=None):
    path = locate_input(filename)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path, sheet_name=sheet_name)


def extract_update_average(filename, requested_series, series_column, period_column, amount_column, current_year, status_column=None, keep_status=None):
    df = load_table(filename)
    subset = df[df[series_column].map(normalize) == normalize(requested_series)].copy()
    if status_column is not None and keep_status is not None:
        subset = subset[subset[status_column].astype(str).str.lower() == keep_status.lower()]
    subset = subset[subset[period_column].astype(str).str.contains(str(current_year))]
    vals = pd.to_numeric(subset[amount_column], errors="coerce").dropna().tolist()
    if not vals:
        raise ValueError(f"No current-year values found for '{requested_series}' in {filename}")
    return float(sum(vals) / len(vals))


def extract_alias_priority_series(annual_workbook, annual_sheet, update_workbook, update_sheet, alias_csv, requested_series, start_year, current_year):
    alias_df = pd.read_csv(locate_input(alias_csv))
    accepted = set(alias_df.loc[alias_df["requested_series"] == requested_series, "accepted_alias"].map(normalize))
    if not accepted:
        raise ValueError(f"No aliases found for requested series '{requested_series}'")

    annual_df = pd.read_excel(locate_input(annual_workbook), sheet_name=annual_sheet)
    annual_df = annual_df[annual_df["target_alias"].map(normalize).isin(accepted)].copy()
    annual_df = annual_df[annual_df["record_type"].astype(str).str.lower() == "official"]
    annual_df["year_num"] = annual_df["year_label"].astype(str).str.extract(r"((?:19|20)\d{2})", expand=False)
    annual_df["year_num"] = pd.to_numeric(annual_df["year_num"], errors="coerce")
    annual_df["priority_num"] = pd.to_numeric(annual_df["priority"], errors="coerce")
    annual_df["amount_num"] = pd.to_numeric(annual_df["amount"], errors="coerce")
    annual_df = annual_df.dropna(subset=["year_num", "priority_num", "amount_num"])
    annual_df["year_num"] = annual_df["year_num"].astype(int)
    annual_df = annual_df.sort_values(["year_num", "priority_num"])

    out = {}
    for year, grp in annual_df.groupby("year_num"):
        if start_year <= int(year) < current_year:
            out[int(year)] = float(grp.iloc[0]["amount_num"])

    update_df = pd.read_excel(locate_input(update_workbook), sheet_name=update_sheet)
    update_df = update_df[update_df["target_alias"].map(normalize).isin(accepted)].copy()
    update_df = update_df[update_df["record_type"].astype(str).str.lower() == "official"]
    update_df = update_df[update_df["subperiod"].astype(str).str.contains(str(current_year))]
    update_df["priority_num"] = pd.to_numeric(update_df["priority"], errors="coerce")
    update_df["amount_num"] = pd.to_numeric(update_df["amount"], errors="coerce")
    update_df = update_df.dropna(subset=["priority_num", "amount_num"])
    update_df = update_df.sort_values(["subperiod", "priority_num"])

    subperiod_values = []
    for _subperiod, grp in update_df.groupby("subperiod"):
        subperiod_values.append(float(grp.iloc[0]["amount_num"]))
    if not subperiod_values:
        raise ValueError(f"No current-year values found for '{requested_series}' after alias filtering")
    out[current_year] = float(sum(subperiod_values) / len(subperiod_values))
    return {yr: out[yr] for yr in sorted(out)}


def extract_register_selected_series(register_csv, requested_series, history_workbook, history_sheet, selector_workbook, selector_sheet, update_files, current_year):
    register = pd.read_csv(locate_input(register_csv))
    match = register[register["requested_series"] == requested_series]
    if match.empty:
        raise ValueError(f"Requested series not found in register: {requested_series}")
    reg = match.iloc[0]

    history_df = pd.read_excel(locate_input(history_workbook), sheet_name=history_sheet)
    hist_subset = history_df[
        (history_df["series_code"] == reg["history_code"]) &
        (history_df["status_bucket"].astype(str).str.lower() == str(reg["history_status"]).lower())
    ]
    if hist_subset.empty:
        raise ValueError(f"No historical row found for {requested_series}")
    row = hist_subset.iloc[0]
    out = {}
    for col in history_df.columns:
        match_year = re.search(r"((?:19|20)\d{2})", str(col))
        if not match_year:
            continue
        yr = int(match_year.group(1))
        if yr < current_year:
            val = pd.to_numeric(row[col], errors="coerce")
            if pd.notna(val):
                out[yr] = float(val)

    selector = pd.read_excel(locate_input(selector_workbook), sheet_name=selector_sheet)
    selector = selector[selector["series_code"] == reg["current_code"]].copy()
    selector = selector.sort_values("month")
    vals = []
    loaded_updates = {}
    for source_key, filename in update_files.items():
        loaded_updates[source_key.upper()] = pd.read_csv(locate_input(filename))

    for _, sel in selector.iterrows():
        src = str(sel["preferred_source"]).upper().strip()
        version = str(sel["preferred_version"]).strip()
        month = str(sel["month"]).strip()
        if src not in loaded_updates:
            continue
        df = loaded_updates[src]
        subset = df[
            (df["series_code"] == reg["current_code"]) &
            (df["month"].astype(str) == month) &
            (df["version"].astype(str) == version)
        ]
        if subset.empty:
            continue
        numeric_vals = pd.to_numeric(subset["amount"], errors="coerce").dropna()
        if not numeric_vals.empty:
            vals.append(float(numeric_vals.iloc[0]))

    if not vals:
        raise ValueError(f"No selected current-year values found for {requested_series}")
    out[current_year] = float(sum(vals) / len(vals))
    return {yr: out[yr] for yr in sorted(out)}, reg["deflator_column"]
