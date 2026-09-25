import json
import math
import re
from pathlib import Path

import pandas as pd
import pytest

DATA_FILE = Path("/root/patient_safety_data.xlsx")
JSON_OUTPUT = Path("/root/patient_safety_report.json")
MD_OUTPUT = Path("/root/patient_safety_brief.md")


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
    p1_df = pd.read_excel(DATA_FILE, sheet_name="Wait Times")
    p2_df = pd.read_excel(DATA_FILE, sheet_name="Medication Errors")
    p3_df = pd.read_excel(DATA_FILE, sheet_name="Readmission Rates")

    p1_vals = p1_df["Patient Wait Time (min)"].dropna().astype(float).tolist()
    denoms = p2_df["Prescriptions Filled"].dropna().astype(float).tolist()
    nums = p2_df["Errors"].dropna().astype(float).tolist()
    p2_rates = [f / n for f, n in zip(nums, denoms)]
    p3_vals = p3_df["Readmission Rate"].dropna().astype(float).tolist()

    p1_slope, p1_t, p1_stability, p1_direction = linear_trend(p1_vals)
    p2_slope, p2_t, p2_stability, p2_direction = linear_trend(p2_rates)
    p3_slope, p3_t, p3_stability, p3_direction = linear_trend(p3_vals)

    total_denom = sum(denoms)
    total_num = sum(nums)
    p2_low, p2_high = wilson_95_pct(total_num, total_denom)
    overall_rate_pct = 100 * total_num / total_denom
    target_rate_pct = 2.0

    ranking = sorted(
        [
            {"process": "wait_times", "cv": cv(p1_vals)},
            {"process": "medication_errors", "cv": cv(p2_rates)},
            {"process": "readmission_rates", "cv": cv(p3_vals)},
        ],
        key=lambda x: x["cv"],
        reverse=True,
    )

    return {
        "wait_times": {
            "n": len(p1_vals),
            "mean": mean(p1_vals),
            "std": sample_std(p1_vals),
            "cv": cv(p1_vals),
            "slope": p1_slope,
            "t_stat": p1_t,
            "stability": p1_stability,
            "direction": p1_direction,
        },
        "medication_errors": {
            "points": len(p2_rates),
            "total_denom": int(total_denom),
            "total_num": int(total_num),
            "overall_rate_pct": overall_rate_pct,
            "ci_low": p2_low,
            "ci_high": p2_high,
            "cv": cv(p2_rates),
            "varying_denominators": len(set(denoms)) > 1,
            "target_rate_pct": target_rate_pct,
            "capability_vs_target": "Capable" if overall_rate_pct <= target_rate_pct else "Not Capable",
            "slope": p2_slope,
            "t_stat": p2_t,
            "stability": p2_stability,
            "direction": p2_direction,
        },
        "readmission_rates": {
            "rows": len(p3_vals),
            "mean": mean(p3_vals),
            "std": sample_std(p3_vals),
            "cv": cv(p3_vals),
            "slope": p3_slope,
            "t_stat": p3_t,
            "stability": p3_stability,
            "direction": p3_direction,
        },
        "ranking": ranking,
    }


def assert_close(actual, expected, tol=1e-3):
    assert abs(actual - expected) <= tol, f"expected {expected}, got {actual}"


def test_required_top_level_keys(outputs):
    report, _ = outputs
    for key in [
        "wait_times",
        "medication_errors",
        "readmission_rates",
        "variability_ranking",
        "highest_variability_process",
        "highest_risk_statement",
        "extended_analysis",
        "monitoring_plan",
    ]:
        assert key in report, f"Missing top-level key: {key}"


def test_process1_metrics(outputs, expected_metrics):
    report, _ = outputs
    p1 = report["wait_times"]
    exp = expected_metrics["wait_times"]

    assert p1["n"] == exp["n"]
    assert_close(p1["mean_min"], exp["mean"], tol=1e-3)
    assert_close(p1["sample_std_min"], exp["std"], tol=1e-3)
    assert_close(p1["cv"], exp["cv"], tol=1e-3)
    assert_close(p1["trend_slope_per_index"], exp["slope"], tol=1e-4)
    assert_close(p1["trend_t_stat"], exp["t_stat"], tol=1e-3)
    assert p1["trend_direction"] == exp["direction"]
    assert p1["stability"] == exp["stability"]
    assert "t-test" in p1["stability_method"].lower()


def test_process2_metrics(outputs, expected_metrics):
    report, _ = outputs
    p2 = report["medication_errors"]
    exp = expected_metrics["medication_errors"]

    assert p2["points"] == exp["points"]
    assert p2["total_prescriptions"] == exp["total_denom"]
    assert p2["total_errors"] == exp["total_num"]
    assert_close(p2["overall_rate_pct"], exp["overall_rate_pct"], tol=1e-3)
    assert len(p2["wilson_95_ci_pct"]) == 2
    assert_close(p2["wilson_95_ci_pct"][0], exp["ci_low"], tol=1e-3)
    assert_close(p2["wilson_95_ci_pct"][1], exp["ci_high"], tol=1e-3)
    assert_close(p2["point_rate_cv"], exp["cv"], tol=1e-3)
    assert p2["uses_varying_denominators"] == exp["varying_denominators"]
    assert_close(p2["target_rate_pct"], exp["target_rate_pct"], tol=1e-9)
    assert p2["capability_vs_target"] == exp["capability_vs_target"]
    assert_close(p2["trend_slope_per_index"], exp["slope"], tol=1e-4)
    assert_close(p2["trend_t_stat"], exp["t_stat"], tol=1e-3)
    assert p2["trend_direction"] == exp["direction"]
    assert p2["stability"] == exp["stability"]


def test_process3_metrics(outputs, expected_metrics):
    report, _ = outputs
    p3 = report["readmission_rates"]
    exp = expected_metrics["readmission_rates"]

    assert p3["rows"] == exp["rows"]
    assert_close(p3["mean_readmission_rate"], exp["mean"], tol=1e-3)
    assert_close(p3["sample_std_readmission_rate"], exp["std"], tol=1e-3)
    assert_close(p3["cv"], exp["cv"], tol=1e-3)
    assert_close(p3["trend_slope_per_index"], exp["slope"], tol=1e-4)
    assert_close(p3["trend_t_stat"], exp["t_stat"], tol=1e-3)
    assert p3["trend_direction"] == exp["direction"]
    assert p3["stability"] == exp["stability"]


def test_variability_ranking_and_highest_risk(outputs, expected_metrics):
    report, _ = outputs
    ranking = report["variability_ranking"]
    expected_ranking = expected_metrics["ranking"]

    assert len(ranking) == 3
    assert [r["process"] for r in ranking] == [r["process"] for r in expected_ranking]

    for actual, expected in zip(ranking, expected_ranking):
        assert_close(actual["cv"], expected["cv"], tol=1e-3)

    assert report["highest_variability_process"] == expected_ranking[0]["process"]
    assert report["highest_variability_process"].strip().lower() == "readmission_rates"
    assert "Readmission Rates is the highest-risk department." in report["highest_risk_statement"]


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
    ]
    for key in required_keys:
        assert key in mp, f"Missing monitoring_plan key: {key}"

    assert isinstance(mp["inputs"], list) and len(mp["inputs"]) >= 2
    assert isinstance(mp["outputs"], list) and len(mp["outputs"]) >= 2
    assert isinstance(mp["key_performance_indicators"], list) and len(mp["key_performance_indicators"]) >= 3
    assert isinstance(mp["prioritized_actions"], list) and len(mp["prioritized_actions"]) >= 3
    assert 5 <= len(mp["checklist"]) <= 9



def test_markdown_sections_and_required_text(outputs):
    _, markdown = outputs

    required_headings = [
        "Summary of Findings",
        "Most Significant Risks",
        "Prioritized Corrective Actions",
    ]

    for heading in required_headings:
        pattern = rf"^#+\s+{re.escape(heading)}\s*$"
        assert re.search(pattern, markdown, flags=re.MULTILINE), f"Missing markdown heading: {heading}"

    assert "Readmission Rates is the highest-risk department." in markdown

    monitoring_headings = [
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
    for heading in monitoring_headings:
        pattern = rf"^#+\s+{re.escape(heading)}\s*$"
        assert re.search(pattern, markdown, flags=re.MULTILINE), f"Missing markdown heading: {heading}"



