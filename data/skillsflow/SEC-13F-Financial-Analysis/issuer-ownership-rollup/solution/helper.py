import json
import os
from pathlib import Path
import pandas as pd
from rapidfuzz import process, fuzz

STOCK_CLASSES = {
    "com","common stock","cl a","com new","class a","stock","common","com cl a","com shs",
    "sponsored adrs","sponsored adr","sponsored ads","adr","equity","cmn","cl b","ord shs",
    "cl a com","class a com","cap stk cl a","comm stk","cl b new","cap stk cl c","cl a new",
    "foreign stock","shs cl a"
}

class FilingToolkit:
    def __init__(self, root="/root"):
        self.root = Path(os.environ.get("TASK_ROOT", root))
        self._cover = {}
        self._info = {}

    def cover(self, quarter):
        if quarter not in self._cover:
            self._cover[quarter] = pd.read_csv(self.root / quarter / "COVERPAGE.tsv", sep="	", dtype=str)
        return self._cover[quarter]

    def info(self, quarter):
        if quarter not in self._info:
            df = pd.read_csv(self.root / quarter / "INFOTABLE.tsv", sep="	", dtype=str)
            df["VALUE"] = df["VALUE"].astype(float)
            df["CUSIP"] = df["CUSIP"].astype(str).str.upper()
            df["TITLEOFCLASS"] = df["TITLEOFCLASS"].fillna("")
            df["NAMEOFISSUER"] = df["NAMEOFISSUER"].fillna("")
            self._info[quarter] = df
        return self._info[quarter]

    def resolve_fund(self, quarter, query):
        cover = self.cover(quarter)
        names = cover["FILINGMANAGER_NAME"].fillna("").unique().tolist()
        match_name, _score, _ = process.extractOne(query, names, scorer=fuzz.WRatio)
        rows = cover[(cover["FILINGMANAGER_NAME"] == match_name) & (cover["ISAMENDMENT"].fillna("N") == "N")]
        if rows.empty:
            rows = cover[cover["FILINGMANAGER_NAME"] == match_name]
        return rows.iloc[0]

    def resolve_issuer(self, quarter, query):
        info = self.info(quarter)
        stocks = info[["CUSIP", "NAMEOFISSUER", "TITLEOFCLASS"]].copy()
        stocks = stocks[stocks["TITLEOFCLASS"].str.lower().isin(STOCK_CLASSES)]
        stocks = stocks.drop_duplicates(subset=["CUSIP"])
        stocks["NAMEOFISSUER"] = stocks["NAMEOFISSUER"].str.lower()
        match_name, _score, _ = process.extractOne(query.lower(), stocks["NAMEOFISSUER"].tolist(), scorer=fuzz.WRatio)
        return stocks[stocks["NAMEOFISSUER"] == match_name].iloc[0]

    def fund_snapshot(self, quarter, accession_number):
        info = self.info(quarter)
        subset = info[info["ACCESSION_NUMBER"] == accession_number].copy()
        subset["CLASS_NORM"] = subset["TITLEOFCLASS"].str.lower()
        stock_rows = subset[subset["CLASS_NORM"].isin(STOCK_CLASSES)].copy()
        grouped = stock_rows.groupby("CUSIP", as_index=False).agg({"NAMEOFISSUER": "first", "VALUE": "sum"})
        return {
            "aum": float(subset["VALUE"].sum()),
            "stock_holdings": int(stock_rows.shape[0]),
            "stock_aum": float(stock_rows["VALUE"].sum()),
            "grouped": grouped,
        }

    def compare_fund(self, current_quarter, current_accession, baseline_quarter, baseline_accession):
        cur = self.fund_snapshot(current_quarter, current_accession)["grouped"].rename(columns={"VALUE": "VALUE_CUR", "NAMEOFISSUER": "NAME_CUR"})
        base = self.fund_snapshot(baseline_quarter, baseline_accession)["grouped"].rename(columns={"VALUE": "VALUE_BASE", "NAMEOFISSUER": "NAME_BASE"})
        merged = cur.merge(base, how="outer", on="CUSIP")
        merged["VALUE_CUR"] = merged["VALUE_CUR"].fillna(0)
        merged["VALUE_BASE"] = merged["VALUE_BASE"].fillna(0)
        merged["NAMEOFISSUER"] = merged["NAME_CUR"].fillna(merged["NAME_BASE"])
        merged["ABS_CHANGE"] = merged["VALUE_CUR"] - merged["VALUE_BASE"]
        return merged.sort_values(["ABS_CHANGE", "CUSIP"], ascending=[False, True])

    def top_holders(self, quarter, cusip, topk):
        info = self.info(quarter)
        cover = self.cover(quarter)
        subset = info[info["CUSIP"] == cusip.upper()].copy()
        agg = subset.groupby("ACCESSION_NUMBER", as_index=False).agg({"VALUE": "sum"})
        agg = agg.sort_values(["VALUE", "ACCESSION_NUMBER"], ascending=[False, True]).head(topk)
        rows = []
        for _, row in agg.iterrows():
            manager = cover[cover["ACCESSION_NUMBER"] == row["ACCESSION_NUMBER"]].iloc[0]["FILINGMANAGER_NAME"]
            rows.append({
                "accession_number": row["ACCESSION_NUMBER"],
                "manager_name": manager,
                "value": float(row["VALUE"]),
            })
        return rows

def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2))
