import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

INPUT_CSV = Path("/root/field_service_data.csv")
OUT_JSON = Path("/root/field_service_analyze_metrics.json")
OUT_MD = Path("/root/field_service_analyze_brief.md")

PRIMARY_START = pd.Timestamp("2025-01-04")
PRIMARY_END = pd.Timestamp("2025-03-01")
IMR_END = pd.Timestamp("2025-02-21")
TARGET = 140.0
BASELINE = 115.0
METRIC_COL = "ClosedWorkOrders"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

DEFINE_START = "2025-02-07"
MEASURE_START = "2025-02-14"
ANALYZE_START = "2025-02-21"
BRIEF_TITLE = "Field Service Analyze Tollgate Brief"

IMPACTS = ['missed service-level commitments', 'repeat truck rolls', 'higher contract penalty exposure', 'customer dissatisfaction escalations']


def _load_df() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
    df.columns = [str(c).strip() for c in df.columns]
    df["Stage"] = df["Stage"].astype(str).str.strip()
    df["Day"] = df["Day"].astype(str).str.strip()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df[METRIC_COL] = pd.to_numeric(df[METRIC_COL], errors="coerce")
    return df.dropna(subset=["Date", METRIC_COL]).sort_values("Date").reset_index(drop=True)


def _expected_metrics():
    df = _load_df()
    primary = df[(df["Date"] >= PRIMARY_START) & (df["Date"] <= PRIMARY_END)].copy()
    primary_biz = primary[primary["Day"].isin(WEEKDAYS)].copy()
    imr = primary[(primary["Date"] <= IMR_END) & (primary["Day"].isin(WEEKDAYS))].copy()

    weekday_means = {
        day: float(primary_biz.loc[primary_biz["Day"] == day, METRIC_COL].mean()) for day in WEEKDAYS
    }
    groups = [primary_biz.loc[primary_biz["Day"] == day, METRIC_COL].to_numpy() for day in WEEKDAYS]
    f_stat, anova_p = stats.f_oneway(*groups)

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
    ci_low, ci_high = stats.t.interval(
        confidence=0.95,
        df=n - 1,
        loc=mean_value,
        scale=std_sample / np.sqrt(n),
    )
    cpk_lower = (mean_value - TARGET) / (3 * std_sample)

    return {
        "counts": (len(primary), len(primary_biz), len(imr)),
        "baseline": BASELINE,
        "target": TARGET,
        "mean_value": mean_value,
        "weekday_means": weekday_means,
        "highest_day": max(weekday_means, key=weekday_means.get),
        "lowest_day": min(weekday_means, key=weekday_means.get),
        "anova_f": float(f_stat),
        "anova_p": float(anova_p),
        "imr_points": len(imr_values),
        "imr_center": imr_center,
        "imr_ucl": imr_ucl,
        "imr_lcl": imr_lcl,
        "mr_bar": mr_bar,
        "mr_ucl": mr_ucl,
        "slope": float(slope),
        "intercept": float(intercept),
        "r_value": float(r_value),
        "reg_p_value": float(reg_p_value),
        "std_err": float(std_err),
        "n": int(n),
        "t_stat": float(t_stat),
        "t_p": float(t_p),
        "ci_low": float(ci_low),
        "ci_high": float(ci_high),
        "std_sample": std_sample,
        "cpk_lower": float(cpk_lower),
    }


def _assert_close(actual, expected, tol=1e-3, label="value"):
    assert math.isfinite(actual), f"{label} is not finite: {actual}"
    assert abs(actual - expected) <= tol, f"{label} mismatch: {actual} vs {expected}"


def test_output_files_exist():
    assert OUT_JSON.exists(), f"Missing {OUT_JSON}"
    assert OUT_MD.exists(), f"Missing {OUT_MD}"


def test_json_structure_and_values():
    expected = _expected_metrics()
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))

    for key in [
        "source_file",
        "filters",
        "record_counts",
        "charter_metrics",
        "anova_by_weekday",
        "imr_summary",
        "regression_day_index",
        "ttest_vs_target",
        "capability_against_lsl",
    ]:
        assert key in payload, f"Missing top-level key: {key}"

    assert payload["source_file"] == "field_service_data.csv"

    total_primary, primary_biz, imr_records = expected["counts"]
    assert payload["record_counts"]["total_primary_records"] == total_primary
    assert payload["record_counts"]["primary_business_day_records"] == primary_biz
    assert payload["record_counts"]["imr_records"] == imr_records

    _assert_close(payload["charter_metrics"]["baseline_value"], expected["baseline"], label="baseline_value")
    _assert_close(payload["charter_metrics"]["target_value"], expected["target"], label="target_value")
    _assert_close(payload["charter_metrics"]["current_mean_value"], expected["mean_value"], label="current_mean_value")

    for day in WEEKDAYS:
        _assert_close(
            payload["anova_by_weekday"]["weekday_means"][day],
            expected["weekday_means"][day],
            label=f"weekday_mean_{day}",
        )
    assert payload["anova_by_weekday"]["highest_mean_day"] == expected["highest_day"]
    assert payload["anova_by_weekday"]["lowest_mean_day"] == expected["lowest_day"]
    _assert_close(payload["anova_by_weekday"]["f_stat"], expected["anova_f"], label="anova_f_stat")
    _assert_close(payload["anova_by_weekday"]["p_value"], expected["anova_p"], label="anova_p_value")

    assert payload["imr_summary"]["points"] == expected["imr_points"]
    _assert_close(payload["imr_summary"]["center_line"], expected["imr_center"], label="imr_center")
    _assert_close(payload["imr_summary"]["ucl"], expected["imr_ucl"], label="imr_ucl")
    _assert_close(payload["imr_summary"]["lcl"], expected["imr_lcl"], label="imr_lcl")
    _assert_close(payload["imr_summary"]["mr_bar"], expected["mr_bar"], label="mr_bar")
    _assert_close(payload["imr_summary"]["mr_ucl"], expected["mr_ucl"], label="mr_ucl")

    _assert_close(payload["regression_day_index"]["slope"], expected["slope"], label="reg_slope")
    _assert_close(payload["regression_day_index"]["intercept"], expected["intercept"], label="reg_intercept")
    _assert_close(payload["regression_day_index"]["r_value"], expected["r_value"], label="reg_r_value")
    _assert_close(payload["regression_day_index"]["p_value"], expected["reg_p_value"], label="reg_p_value")
    _assert_close(payload["regression_day_index"]["std_err"], expected["std_err"], label="reg_std_err")

    assert payload["ttest_vs_target"]["n"] == expected["n"]
    _assert_close(payload["ttest_vs_target"]["mean_value"], expected["mean_value"], label="ttest_mean")
    _assert_close(payload["ttest_vs_target"]["t_stat"], expected["t_stat"], label="ttest_stat")
    _assert_close(payload["ttest_vs_target"]["p_value"], expected["t_p"], label="ttest_p")
    _assert_close(payload["ttest_vs_target"]["ci95_low"], expected["ci_low"], label="ttest_ci_low")
    _assert_close(payload["ttest_vs_target"]["ci95_high"], expected["ci_high"], label="ttest_ci_high")
    expected_decision = "reject_h0" if expected["t_p"] < 0.05 else "fail_to_reject_h0"
    assert payload["ttest_vs_target"]["decision"] == expected_decision

    _assert_close(payload["capability_against_lsl"]["lsl"], expected["target"], label="capability_lsl")
    _assert_close(
        payload["capability_against_lsl"]["std_dev_sample"],
        expected["std_sample"],
        label="capability_std_sample",
    )
    _assert_close(payload["capability_against_lsl"]["cpk_lower"], expected["cpk_lower"], label="cpk_lower")


def test_markdown_structure_and_content():
    text = OUT_MD.read_text(encoding="utf-8")

    required_headers = [
        f"# {BRIEF_TITLE}",
        "## Project Charter",
        "## Statistical Analysis",
        "## A3 Summary",
        "## Timeline and Next Steps",
    ]
    for h in required_headers:
        assert h in text, f"Missing header: {h}"

    required_subsections = [
        "### One-Way ANOVA",
        "### I-MR Control Chart",
        "### Linear Regression (ClosedWorkOrders ~ day_index)",
        "### One-Sample t-Test vs 140",
        "### Process Capability",
    ]
    for s in required_subsections:
        assert s in text, f"Missing subsection: {s}"

    hit_count = sum(1 for i in IMPACTS if i in text)
    assert hit_count >= 2, "Need at least two required operational impacts in markdown"

    for d in [DEFINE_START, MEASURE_START, ANALYZE_START]:
        assert d in text, f"Missing timeline date: {d}"

    march_due_dates = re.findall(r"2025-03-\d{2}", text)
    assert len(march_due_dates) >= 2, "Need at least two March 2025 due dates in next steps"
    assert "Owner:" in text, "Next steps must include owners"
