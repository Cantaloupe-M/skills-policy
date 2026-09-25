import pandas as pd

def parse_value(value):
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s == '' or s.lower() == 'nan':
        return None
    if ',' in s:
        s = s.replace(',', '.')
    return float(s)

def convert_value(v, mode, factor, lo, hi):
    if v is None:
        return None
    if lo <= v <= hi:
        return v
    if mode == 'single':
        c = v / factor
        return c if lo <= c <= hi else v
    if mode == 'single-reverse':
        c = v * factor
        return c if lo <= c <= hi else v
    return v

def normalize_frame(df, specs, id_column=None, keep_columns=None):
    numeric_cols = [c for c in df.columns if c != id_column]
    if keep_columns is not None:
        numeric_cols = [c for c in numeric_cols if c in keep_columns]
    missing_mask = df[numeric_cols].applymap(lambda x: pd.isna(x) or str(x).strip() == '' or str(x).strip().lower() == 'nan').any(axis=1)
    df = df.loc[~missing_mask].copy()
    for col in numeric_cols:
        mode, factor, lo, hi = specs[col]
        df[col] = df[col].apply(parse_value)
        df[col] = df[col].apply(lambda x: convert_value(x, mode, factor, lo, hi))
        df[col] = df[col].apply(lambda x: f"{x:.2f}")
    return df
