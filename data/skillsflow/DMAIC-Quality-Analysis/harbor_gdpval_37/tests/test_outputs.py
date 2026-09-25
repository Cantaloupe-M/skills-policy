import json
import math
import re
from pathlib import Path

import pandas as pd
import pytest

DATA_FILE = Path("/root/process_capability_data.xlsx")
JSON_OUTPUT = Path("/root/process_capability_report.json")
MD_OUTPUT = Path("/root/process_capability_brief.md")


def mean(values):
    return sum(values) / len(values)


def sample_std(values):
    m = mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def cv(values):
    m = mean(values)
    return sample_std(values) / m


def linear_trend(values):
    n = len(values)
    x_vals = list(range(1, n + 1))
    sx = sum(x_vals)
    sy = sum(values)
    sxx = sum(x * x for x in x_vals)
    sxy = sum(x * y for x, y in zip(x_vals, values))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    intercept = (sy - slope * sx) / n

    x_bar = sx / n
    ssx = sum((x - x_bar) ** 2 for x in x_vals)
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(x_vals, values))
    se_slope = math.sqrt((sse / (n - 2)) / ssx)
    t_stat = 0.0 if se_slope == 0 else slope / se_slope

    if slope > 0:
        direction = "increasing"
    elif slope < 0:
        direction = "decreasing"
    else:
        direction = "flat"

    stability = "Stable" if abs(t_stat) < 2.0 else "Unstable"
    return slope, t_stat, stability, direction


def wilson_95_pct(successes, n, z=1.959963984540054):
    p = successes / n
    denom = 1 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + (z * z) / (4 * n)) / n) / denom
    return 100 * (center - half), 100 * (center + half)


@pytest.fixture(scope="module")
def outputs():
    assert JSON_OUTPUT.exists(), f"Missing output JSON: {JSON_OUTPUT}"
    assert MD_OUTPUT.exists(), f"Missing output Markdown: {MD_OUTPUT}"

    report = json.loads(JSON_OUTPUT.read_text(encoding="utf-8"))
    markdown = MD_OUTPUT.read_text(encoding="utf-8")
    return report, markdown


@pytest.fixture(scope="module")
def expected_metrics():
    td_df = pd.read_excel(DATA_FILE, sheet_name="Task Duration")
    fr_df = pd.read_excel(DATA_FILE, sheet_name="Failure Rate")
    se_df = pd.read_excel(DATA_FILE, sheet_name="System Errors")

    td_vals = td_df["Process Duration (min)"].dropna().astype(float).tolist()
    units = fr_df["Units processed"].dropna().astype(float).tolist()
    fails = fr_df["Failures"].dropna().astype(float).tolist()
    fr_rates = [f / n for f, n in zip(fails, units)]
    se_rates = se_df["Error Rate"].dropna().astype(float).tolist()

    td_slope, td_t, td_stability, td_direction = linear_trend(td_vals)
    fr_slope, fr_t, fr_stability, fr_direction = linear_trend(fr_rates)
    se_slope, se_t, se_stability, se_direction = linear_trend(se_rates)

    total_units = sum(units)
    total_fails = sum(fails)
    fr_low, fr_high = wilson_95_pct(total_fails, total_units)
    overall_rate_pct = 100 * total_fails / total_units
    target_rate_pct = 1.0

    ranking = sorted(
        [
            {"process": "task_duration", "cv": cv(td_vals)},
            {"process": "failure_rate", "cv": cv(fr_rates)},
            {"process": "system_errors", "cv": cv(se_rates)},
        ],
        key=lambda x: x["cv"],
        reverse=True,
    )

    return {
        "task_duration": {
            "n": len(td_vals),
            "mean": mean(td_vals),
            "std": sample_std(td_vals),
            "cv": cv(td_vals),
            "slope": td_slope,
            "t_stat": td_t,
            "stability": td_stability,
            "direction": td_direction,
        },
        "failure_rate": {
            "points": len(fr_rates),
            "total_units": int(total_units),
            "total_fails": int(total_fails),
            "overall_rate_pct": overall_rate_pct,
            "ci_low": fr_low,
            "ci_high": fr_high,
            "cv": cv(fr_rates),
            "varying_denominators": len(set(units)) > 1,
            "target_rate_pct": target_rate_pct,
            "capability_vs_target": "Capable" if overall_rate_pct <= target_rate_pct else "Not Capable",
            "slope": fr_slope,
            "t_stat": fr_t,
            "stability": fr_stability,
            "direction": fr_direction,
        },
        "system_errors": {
            "rows": len(se_rates),
            "mean": mean(se_rates),
            "std": sample_std(se_rates),
            "cv": cv(se_rates),
            "slope": se_slope,
            "t_stat": se_t,
            "stability": se_stability,
            "direction": se_direction,
        },
        "ranking": ranking,
    }


def assert_close(actual, expected, tol=1e-3):
    assert abs(actual - expected) <= tol, f"expected {expected}, got {actual}"


def test_required_top_level_keys(outputs):
    report, _ = outputs
    for key in [
        "task_duration",
        "failure_rate",
        "system_errors",
        "variability_ranking",
        "highest_variability_process",
        "highest_risk_statement",
        "extended_analysis",
        "monitoring_plan",
    ]:
        assert key in report, f"Missing top-level key: {key}"


def test_task_duration_metrics(outputs, expected_metrics):
    report, _ = outputs
    td = report["task_duration"]
    exp = expected_metrics["task_duration"]

    assert td["n"] == exp["n"]
    assert_close(td["mean_min"], exp["mean"], tol=1e-3)
    assert_close(td["sample_std_min"], exp["std"], tol=1e-3)
    assert_close(td["cv"], exp["cv"], tol=1e-3)
    assert_close(td["trend_slope_per_index"], exp["slope"], tol=1e-4)
    assert_close(td["trend_t_stat"], exp["t_stat"], tol=1e-3)
    assert td["trend_direction"] == exp["direction"]
    assert td["stability"] == exp["stability"]
    assert "t-test" in td["stability_method"].lower()


def test_failure_rate_metrics(outputs, expected_metrics):
    report, _ = outputs
    fr = report["failure_rate"]
    exp = expected_metrics["failure_rate"]

    assert fr["points"] == exp["points"]
    assert fr["total_units"] == exp["total_units"]
    assert fr["total_failures"] == exp["total_fails"]
    assert_close(fr["overall_rate_pct"], exp["overall_rate_pct"], tol=1e-3)
    assert len(fr["wilson_95_ci_pct"]) == 2
    assert_close(fr["wilson_95_ci_pct"][0], exp["ci_low"], tol=1e-3)
    assert_close(fr["wilson_95_ci_pct"][1], exp["ci_high"], tol=1e-3)
    assert_close(fr["point_rate_cv"], exp["cv"], tol=1e-3)
    assert fr["uses_varying_denominators"] == exp["varying_denominators"]
    assert_close(fr["target_rate_pct"], exp["target_rate_pct"], tol=1e-9)
    assert fr["capability_vs_target"] == exp["capability_vs_target"]
    assert_close(fr["trend_slope_per_index"], exp["slope"], tol=1e-4)
    assert_close(fr["trend_t_stat"], exp["t_stat"], tol=1e-3)
    assert fr["trend_direction"] == exp["direction"]
    assert fr["stability"] == exp["stability"]


def test_system_error_metrics(outputs, expected_metrics):
    report, _ = outputs
    se = report["system_errors"]
    exp = expected_metrics["system_errors"]

    assert se["rows"] == exp["rows"]
    assert_close(se["mean_error_rate"], exp["mean"], tol=1e-3)
    assert_close(se["sample_std_error_rate"], exp["std"], tol=1e-3)
    assert_close(se["cv"], exp["cv"], tol=1e-3)
    assert_close(se["trend_slope_per_index"], exp["slope"], tol=1e-4)
    assert_close(se["trend_t_stat"], exp["t_stat"], tol=1e-3)
    assert se["trend_direction"] == exp["direction"]
    assert se["stability"] == exp["stability"]


def test_variability_ranking_and_highest_risk(outputs, expected_metrics):
    report, _ = outputs
    ranking = report["variability_ranking"]
    expected_ranking = expected_metrics["ranking"]

    assert len(ranking) == 3
    assert [r["process"] for r in ranking] == [r["process"] for r in expected_ranking]

    for actual, expected in zip(ranking, expected_ranking):
        assert_close(actual["cv"], expected["cv"], tol=1e-3)

    assert report["highest_variability_process"] == expected_ranking[0]["process"]
    assert report["highest_variability_process"].strip().lower() == "system_errors"
    assert "System Errors is the highest-risk process." in report["highest_risk_statement"]


def test_extended_analysis_consistency(outputs):
    report, _ = outputs
    ext = report["extended_analysis"]
    highest = report["highest_variability_process"]

    assert ext["process"] == highest
    assert isinstance(ext["capability_evaluation"], str) and len(ext["capability_evaluation"]) > 20
    assert isinstance(ext["stability_assessment"], str) and len(ext["stability_assessment"]) > 20
    assert isinstance(ext["priority_reason"], str) and len(ext["priority_reason"]) > 20
    assert ext["time_trend_review"]["direction"] in {"increasing", "decreasing", "flat"}


def test_monitoring_plan_schema(outputs):
    report, _ = outputs
    mp = report["monitoring_plan"]

    required_keys = [
        "process_to_be_monitored",
        "inputs",
        "outputs",
        "key_performance_indicators",
        "frequency_of_monitoring",
        "observation_format",
        "roles",
        "reporting_format",
        "corrective_action_process",
        "benchmarks",
        "prioritized_actions",
        "checklist",
        "momentum_plan_30_60_90",
        "project_codename",
    ]
    for key in required_keys:
        assert key in mp, f"Missing monitoring_plan key: {key}"

    assert isinstance(mp["inputs"], list) and len(mp["inputs"]) >= 2
    assert isinstance(mp["outputs"], list) and len(mp["outputs"]) >= 2
    assert isinstance(mp["key_performance_indicators"], list) and len(mp["key_performance_indicators"]) >= 3
    assert isinstance(mp["prioritized_actions"], list) and len(mp["prioritized_actions"]) >= 3
    assert 5 <= len(mp["checklist"]) <= 9
    assert all(k in mp["momentum_plan_30_60_90"] for k in ["day_30", "day_60", "day_90"])
    assert isinstance(mp["project_codename"], str) and len(mp["project_codename"]) > 0


def test_markdown_sections_and_required_text(outputs):
    _, markdown = outputs

    required_headings = [
        "Summary of Findings",
        "Most Significant Risks",
        "Prioritized Corrective Actions",
        "Monitoring Plan",
        "Process to be Monitored",
        "Inputs",
        "Outputs",
        "Key Performance Indicators (KPIs)",
        "Frequency of Monitoring",
        "Observation Format",
        "Roles",
        "Reporting Format",
        "Corrective Action Process",
        "Benchmarks",
    ]

    for heading in required_headings:
        pattern = rf"^#+\s+{re.escape(heading)}\s*$"
        assert re.search(pattern, markdown, flags=re.MULTILINE), f"Missing markdown heading: {heading}"

    assert "System Errors is the highest-risk process." in markdown
    assert re.search(r"project codename\s*:", markdown, flags=re.IGNORECASE)
    assert re.search(r"30-day milestone", markdown, flags=re.IGNORECASE)
    assert re.search(r"60-day milestone", markdown, flags=re.IGNORECASE)
    assert re.search(r"90-day milestone", markdown, flags=re.IGNORECASE)
