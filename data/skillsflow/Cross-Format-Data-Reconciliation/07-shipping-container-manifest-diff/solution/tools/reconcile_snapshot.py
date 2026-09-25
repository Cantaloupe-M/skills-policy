#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pdfplumber


def to_python_value(value, field, int_columns, float_columns):
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if field in int_columns:
        return int(round(float(value)))
    if field in float_columns:
        return round(float(value), 2)
    return str(value).strip()


def read_pdf_table(pdf_path, id_pattern, int_columns, float_columns):
    rows = []
    headers = None
    compiled = re.compile(id_pattern)

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables() or []:
                for row in table or []:
                    if not row:
                        continue
                    cleaned = [" ".join(str(cell).split()) if cell is not None else "" for cell in row]
                    if not any(cleaned):
                        continue
                    if headers is None and cleaned[0] == "ID":
                        headers = cleaned
                        continue
                    if headers is None:
                        continue
                    if cleaned[0] == "ID":
                        continue
                    if len(cleaned) < len(headers):
                        cleaned = cleaned + [""] * (len(headers) - len(cleaned))
                    cleaned = cleaned[: len(headers)]
                    cleaned = [value.replace(" ", "") if headers[idx] == "ID" else value for idx, value in enumerate(cleaned)]
                    if compiled.fullmatch(cleaned[0]):
                        rows.append(cleaned)

    if headers is None or not rows:
        raise RuntimeError(f"Failed to extract structured table from {pdf_path}")

    df = pd.DataFrame(rows, columns=headers)
    for col in int_columns + float_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.replace("$", "", regex=False),
                errors="coerce",
            )
    return df


def read_excel_table(excel_path, int_columns, float_columns):
    df = pd.read_excel(excel_path, dtype={"ID": str})
    for col in int_columns + float_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def compare_data(df_old, df_new, deleted_key, modified_key, int_columns, float_columns):
    result = {deleted_key: [], modified_key: []}
    old_ids = set(df_old["ID"].astype(str).tolist())
    new_ids = set(df_new["ID"].astype(str).tolist())
    result[deleted_key] = sorted(old_ids - new_ids)

    df_old_indexed = df_old.copy()
    df_new_indexed = df_new.copy()
    df_old_indexed["ID"] = df_old_indexed["ID"].astype(str)
    df_new_indexed["ID"] = df_new_indexed["ID"].astype(str)
    df_old_indexed = df_old_indexed.set_index("ID")
    df_new_indexed = df_new_indexed.set_index("ID")

    modified = []
    for item_id in sorted(old_ids & new_ids):
        old_row = df_old_indexed.loc[item_id]
        new_row = df_new_indexed.loc[item_id]
        for field in df_old.columns:
            if field == "ID":
                continue
            old_val = to_python_value(old_row[field], field, int_columns, float_columns)
            new_val = to_python_value(new_row[field], field, int_columns, float_columns)
            if old_val != new_val:
                modified.append(
                    {
                        "id": item_id,
                        "field": field,
                        "old_value": old_val,
                        "new_value": new_val,
                    }
                )

    result[modified_key] = sorted(modified, key=lambda item: (item["id"], item["field"]))
    return result


def main(config_path):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    old_df = read_pdf_table(config["pdf_file"], config["id_pattern"], config["int_columns"], config["float_columns"])
    new_df = read_excel_table(config["excel_file"], config["int_columns"], config["float_columns"])
    result = compare_data(
        old_df,
        new_df,
        config["deleted_key"],
        config["modified_key"],
        config["int_columns"],
        config["float_columns"],
    )
    Path(config["output_file"]).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: reconcile_snapshot.py <task_config.json>")
    main(sys.argv[1])
