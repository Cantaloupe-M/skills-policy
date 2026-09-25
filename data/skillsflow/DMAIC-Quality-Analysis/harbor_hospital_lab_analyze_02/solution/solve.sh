#!/bin/bash
set -euo pipefail

python3 <<'PY'
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

INPUT_CSV = Path("/root/lab_panel_data.csv")
OUT_JSON = Path("/root/lab_analyze_metrics.json")
OUT_MD = Path("/root/lab_analyze_brief.md")

PRIMARY_START = pd.Timestamp("2025-01-04")
PRIMARY_END = pd.Timestamp("2025-03-01")
IMR_END = pd.Timestamp("2025-02-21")
TARGET = 810.0
BASELINE = 740.0
METRIC_COL = "CompletedPanels"
METRIC_LABEL = "completed lab panels"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def load_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    df.columns = [str(c).strip() for c in df.columns]
    df["Stage"] = df["Stage"].astype(str).str.strip()
    df["Day"] = df["Day"].astype(str).str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df[METRIC_COL] = pd.to_numeric(df[METRIC_COL], errors="coerce")
    return df.dropna(subset=["Date", METRIC_COL]).sort_values("Date").reset_index(drop=True)


def main() -> None:
    df = load_data()
    primary = df[(df["Date"] >= PRIMARY_START) & (df["Date"] <= PRIMARY_END)].copy()
    primary_biz = primary[primary["Day"].isin(WEEKDAYS)].copy()
    imr = primary[(primary["Date"] <= IMR_END) & (primary["Day"].isin(WEEKDAYS))].copy()

    weekday_means = {
        day: float(primary_biz.loc[primary_biz["Day"] == day, METRIC_COL].mean())
        for day in WEEKDAYS
    }
    groups = [primary_biz.loc[primary_biz["Day"] == day, METRIC_COL].to_numpy() for day in WEEKDAYS]
    f_stat, anova_p = stats.f_oneway(*groups)
    highest_mean_day = max(weekday_means, key=weekday_means.get)
    lowest_mean_day = min(weekday_means, key=weekday_means.get)

    imr_values = imr[METRIC_COL].to_numpy(dtype=float)
    mr_values = np.abs(np.diff(imr_values))
    mr_bar = float(mr_values.mean())
    sigma = mr_bar / 1.128
    imr_center = float(imr_values.mean())
    imr_ucl = float(imr_center + 3 * sigma)
    imr_lcl = float(imr_center - 3 * sigma)
    mr_ucl = float(3.267 * mr_bar)

    reg_x = np.arange(1, len(primary_biz) + 1, dtype=float)
    reg_y = primary_biz[METRIC_COL].to_numpy(dtype=float)
    slope, intercept, r_value, reg_p_value, std_err = stats.linregress(reg_x, reg_y)

    t_stat, t_p = stats.ttest_1samp(reg_y, popmean=TARGET)
    n = len(reg_y)
    mean_value = float(reg_y.mean())
    std_sample = float(reg_y.std(ddof=1))
    t_ci_low, t_ci_high = stats.t.interval(
        confidence=0.95,
        df=n - 1,
        loc=mean_value,
        scale=std_sample / np.sqrt(n),
    )
    decision = "reject_h0" if t_p < 0.05 else "fail_to_reject_h0"
    cpk_lower = (mean_value - TARGET) / (3 * std_sample)

    payload = {
        "source_file": "lab_panel_data.csv",
        "filters": {
            "primary_start": "2025-01-04",
            "primary_end": "2025-03-01",
            "business_days_only": True,
            "imr_end": "2025-02-21",
        },
        "record_counts": {
            "total_primary_records": int(len(primary)),
            "primary_business_day_records": int(len(primary_biz)),
            "imr_records": int(len(imr)),
        },
        "charter_metrics": {
            "baseline_value": BASELINE,
            "target_value": TARGET,
            "current_mean_value": mean_value,
        },
        "anova_by_weekday": {
            "f_stat": float(f_stat),
            "p_value": float(anova_p),
            "weekday_means": weekday_means,
            "highest_mean_day": highest_mean_day,
            "lowest_mean_day": lowest_mean_day,
        },
        "imr_summary": {
            "points": int(len(imr_values)),
            "center_line": imr_center,
            "ucl": imr_ucl,
            "lcl": imr_lcl,
            "mr_bar": mr_bar,
            "mr_ucl": mr_ucl,
        },
        "regression_day_index": {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_value": float(r_value),
            "p_value": float(reg_p_value),
            "std_err": float(std_err),
        },
        "ttest_vs_target": {
            "n": int(n),
            "mean_value": mean_value,
            "t_stat": float(t_stat),
            "p_value": float(t_p),
            "ci95_low": float(t_ci_low),
            "ci95_high": float(t_ci_high),
            "decision": decision,
        },
        "capability_against_lsl": {
            "lsl": TARGET,
            "std_dev_sample": std_sample,
            "cpk_lower": float(cpk_lower),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md = f"""# Clinical Lab Analyze Tollgate Brief

## Project Charter
- Domain objective: improve completed lab panels under a DMAIC Analyze gate.
- Baseline value: {BASELINE:.0f}
- Target value: {TARGET:.0f}
- Current mean value (business days, 2025-01-04..2025-03-01): {mean_value:.2f}
- Operational impacts: delayed patient discharge decisions, repeat specimen requests, higher overtime in lab operations, escalated clinician callbacks.

## Statistical Analysis
### One-Way ANOVA
- Weekday means: Monday {weekday_means['Monday']:.2f}, Tuesday {weekday_means['Tuesday']:.2f}, Wednesday {weekday_means['Wednesday']:.2f}, Thursday {weekday_means['Thursday']:.2f}, Friday {weekday_means['Friday']:.2f}
- F-statistic: {f_stat:.6f}
- p-value: {anova_p:.6f}
- Highest weekday mean: {highest_mean_day}
- Lowest weekday mean: {lowest_mean_day}

### I-MR Control Chart
- Window: 2025-01-04..2025-02-21, business days only
- Points: {len(imr_values)}
- I center line: {imr_center:.2f}
- I UCL/LCL: {imr_ucl:.2f} / {imr_lcl:.2f}
- MR-bar: {mr_bar:.2f}
- MR UCL: {mr_ucl:.2f}

### Linear Regression (CompletedPanels ~ day_index)
- Slope: {slope:.6f}
- Intercept: {intercept:.6f}
- r-value: {r_value:.6f}
- p-value: {reg_p_value:.6f}

### One-Sample t-Test vs 810
- n: {n}
- Mean value: {mean_value:.2f}
- t-statistic: {t_stat:.6f}
- p-value: {t_p:.6f}
- 95% CI: [{t_ci_low:.2f}, {t_ci_high:.2f}]
- Decision at alpha=0.05: {decision}

### Process Capability
- LSL: {TARGET:.0f}
- Sample standard deviation: {std_sample:.4f}
- Cpk (lower): {cpk_lower:.6f}

## A3 Summary
- Background: current business-day throughput remains below target requirements.
- Purpose: quantify variation and trend behavior before Improve-phase actions.
- Current Conditions: mean performance is {mean_value:.2f} against target {TARGET:.0f}.
- Analysis Results: weekday effects, control-chart behavior, trend signal, hypothesis-test outcome, and capability estimate.
- Follow-up: finalize prioritized actions and convert them into controlled operational checks.

## Timeline and Next Steps
- Define start: 2025-02-03
- Measure start: 2025-02-10
- Analyze start: 2025-02-17
- Improve: TBD
- Control: TBD

1. Finalize Analyze package and leadership readout (Owner: Lab Process Engineer, Due: 2025-03-12)
2. Launch weekly monitoring and exception review cadence (Owner: Pathology Operations Manager, Due: 2025-03-26)
"""
    OUT_MD.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
PY
