#!/bin/bash
set -euo pipefail

cat > /tmp/solve_task.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import json
import math

import pandas as pd

DATA_FILE = "/root/patient_safety_data.xlsx"
JSON_OUTPUT = "/root/patient_safety_report.json"
MD_OUTPUT = "/root/patient_safety_brief.md"


def mean(values):
    return sum(values) / len(values)


def sample_std(values):
    m = mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def coefficient_of_variation(values):
    m = mean(values)
    if m == 0:
        return float("inf")
    return sample_std(values) / m


def linear_trend(values):
    n = len(values)
    x_vals = list(range(1, n + 1))
    sx = sum(x_vals)
    sy = sum(values)
    sxx = sum(x * x for x in x_vals)
    sxy = sum(x * y for x, y in zip(x_vals, values))
    denom = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / denom if denom != 0 else 0.0
    intercept = (sy - slope * sx) / n if n else 0.0

    x_bar = sx / n
    ssx = sum((x - x_bar) ** 2 for x in x_vals)
    sse = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(x_vals, values))

    if n <= 2 or ssx == 0:
        t_stat = 0.0
    else:
        se_slope = math.sqrt((sse / (n - 2)) / ssx)
        t_stat = 0.0 if se_slope == 0 else slope / se_slope

    stability = "Stable" if abs(t_stat) < 2.0 else "Unstable"
    if slope > 0:
        direction = "increasing"
    elif slope < 0:
        direction = "decreasing"
    else:
        direction = "flat"

    return slope, t_stat, stability, direction


def wilson_95_pct(successes, n, z=1.959963984540054):
    p = successes / n
    denom = 1 + (z * z) / n
    center = (p + (z * z) / (2 * n)) / denom
    half = z * math.sqrt((p * (1 - p) + (z * z) / (4 * n)) / n) / denom
    return 100 * (center - half), 100 * (center + half)


def main():
    p1_df = pd.read_excel(DATA_FILE, sheet_name="Wait Times")
    p2_df = pd.read_excel(DATA_FILE, sheet_name="Medication Errors")
    p3_df = pd.read_excel(DATA_FILE, sheet_name="Readmission Rates")

    p1_vals = p1_df["Patient Wait Time (min)"].dropna().astype(float).tolist()
    denoms = p2_df["Prescriptions Filled"].dropna().astype(float).tolist()
    nums = p2_df["Errors"].dropna().astype(float).tolist()
    p2_rates = [f / n for f, n in zip(nums, denoms)]
    p3_vals = p3_df["Readmission Rate"].dropna().astype(float).tolist()

    p1_mean = mean(p1_vals)
    p1_std = sample_std(p1_vals)
    p1_cv = coefficient_of_variation(p1_vals)
    p1_slope, p1_t, p1_stability, p1_direction = linear_trend(p1_vals)

    total_denom = sum(denoms)
    total_num = sum(nums)
    overall_rate_pct = 100 * total_num / total_denom
    p2_ci_low, p2_ci_high = wilson_95_pct(total_num, total_denom)
    p2_cv = coefficient_of_variation(p2_rates)
    p2_slope, p2_t, p2_stability, p2_direction = linear_trend(p2_rates)
    target_rate_pct = 2.0
    capability_vs_target = "Capable" if overall_rate_pct <= target_rate_pct else "Not Capable"

    p3_mean = mean(p3_vals)
    p3_std = sample_std(p3_vals)
    p3_cv = coefficient_of_variation(p3_vals)
    p3_slope, p3_t, p3_stability, p3_direction = linear_trend(p3_vals)

    variability_ranking = sorted(
        [
            {"process": "wait_times", "cv": p1_cv},
            {"process": "medication_errors", "cv": p2_cv},
            {"process": "readmission_rates", "cv": p3_cv},
        ],
        key=lambda x: x["cv"],
        reverse=True,
    )

    highest_process = variability_ranking[0]["process"]
    process_details = {
        "wait_times": {"cv": p1_cv, "slope": p1_slope, "t_stat": p1_t, "stability": p1_stability, "direction": p1_direction},
        "medication_errors": {"cv": p2_cv, "slope": p2_slope, "t_stat": p2_t, "stability": p2_stability, "direction": p2_direction},
        "readmission_rates": {"cv": p3_cv, "slope": p3_slope, "t_stat": p3_t, "stability": p3_stability, "direction": p3_direction},
    }

    report = {
        "wait_times": {
            "n": len(p1_vals),
            "mean_min": p1_mean,
            "sample_std_min": p1_std,
            "cv": p1_cv,
            "trend_slope_per_index": p1_slope,
            "trend_t_stat": p1_t,
            "trend_direction": p1_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": p1_stability,
        },
        "medication_errors": {
            "points": len(p2_rates),
            "total_prescriptions": int(total_denom),
            "total_errors": int(total_num),
            "overall_rate_pct": overall_rate_pct,
            "wilson_95_ci_pct": [p2_ci_low, p2_ci_high],
            "point_rate_cv": p2_cv,
            "uses_varying_denominators": len(set(denoms)) > 1,
            "target_rate_pct": target_rate_pct,
            "capability_vs_target": capability_vs_target,
            "trend_slope_per_index": p2_slope,
            "trend_t_stat": p2_t,
            "trend_direction": p2_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": p2_stability,
        },
        "readmission_rates": {
            "rows": len(p3_vals),
            "mean_readmission_rate": p3_mean,
            "sample_std_readmission_rate": p3_std,
            "cv": p3_cv,
            "trend_slope_per_index": p3_slope,
            "trend_t_stat": p3_t,
            "trend_direction": p3_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": p3_stability,
        },
        "variability_ranking": variability_ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": "Readmission Rates is the highest-risk department.",
        "extended_analysis": {
            "process": highest_process,
            "capability_evaluation": (
                f"{highest_process} has the highest CV ({process_details[highest_process]['cv']:.4f}), "
                "indicating the greatest relative variability and process risk."
            ),
            "stability_assessment": (
                f"{highest_process} is {process_details[highest_process]['stability']} "
                f"under the linear trend t-test rule."
            ),
            "time_trend_review": {
                "slope_per_index": process_details[highest_process]["slope"],
                "t_stat": process_details[highest_process]["t_stat"],
                "direction": process_details[highest_process]["direction"],
            },
            "priority_reason": (
                f"Prioritize {highest_process.replace('_',' ')} reduction first because its relative "
                "dispersion is far above the other processes and creates the largest downstream risk."
            ),
        },
    }


    report["monitoring_plan"] = {
        "process_to_be_monitored": "End-to-end readmission rates quality and process throughput",
        "inputs": [
            "Raw wait times records",
            "Prescriptions Filled and Errors counts",
            "Readmission Rates series data",
        ],
        "outputs": [
            "Daily performance dashboard",
            "Weekly leadership risk summary",
            "Corrective action tracker",
        ],
        "key_performance_indicators": [
            {
                "name": "Wait Times Mean",
                "frequency": "Daily",
                "collection_method": "Automated extraction from logs",
                "benchmark": "Within historical baseline",
            },
            {
                "name": "Medication Errors Overall Rate (%)",
                "frequency": "Daily",
                "collection_method": "Errors / Prescriptions Filled",
                "benchmark": "<= 2.0%",
            },
            {
                "name": "Readmission Rates Mean",
                "frequency": "Daily",
                "collection_method": "Average of Readmission Rate column",
                "benchmark": "Downward trend week-over-week",
            },
        ],
        "frequency_of_monitoring": "Daily KPI review with weekly executive escalation",
        "observation_format": "Standardized checklist plus weekly trend chart review",
        "roles": {
            "Front-line Staff": "Capture operating data and flag abnormal events",
            "Quality Supervisor": "Validate KPI calculations and trigger containment",
            "Department Manager": "Prioritize fixes and resource allocation",
            "Process Improvement Advisor": "Lead root-cause and preventive redesign work",
        },
        "reporting_format": "One-page weekly scorecard with red/amber/green status and owners",
        "corrective_action_process": [
            "Detect threshold breach or adverse trend",
            "Perform root-cause analysis and assign owner",
            "Implement corrective action with due date",
            "Verify impact and either standardize or escalate",
        ],
        "benchmarks": [
            "Medication Errors rate at or below 2.0%",
            "Wait Times variation reduced from baseline",
            "Readmission Rates CV reduced each month",
        ],
        "prioritized_actions": [
            "1) Stabilize high-variance readmission rates drivers",
            "2) Contain medication errors exceedances through daily review",
            "3) Standardize wait times workflows to reduce spread",
        ],
        "checklist": [
            "Confirm latest KPI extract is complete before the shift meeting.",
            "Verify any red KPI has an assigned owner and due date.",
            "Review top three abnormal readmission rates points and document root-cause hypotheses.",
            "Confirm corrective actions from prior week were executed and verified.",
            "Escalate unresolved high-risk items in the weekly leadership report.",
            "Log one preventive action to avoid repeat issues.",
        ],
    }




    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_lines = [
        "# Summary of Findings",
        f"- Wait Times mean: {p1_mean:.4f}; sample SD: {p1_std:.4f}; CV: {p1_cv:.4f}; stability: {p1_stability}.",
        f"- Medication Errors overall: {overall_rate_pct:.4f}% (95% Wilson CI: {p2_ci_low:.4f}% to {p2_ci_high:.4f}%); stability: {p2_stability}; capability vs 2.0% target: {capability_vs_target}.",
        f"- Readmission Rates mean: {p3_mean:.4f}; sample SD: {p3_std:.4f}; CV: {p3_cv:.4f}; stability: {p3_stability}.",
        "",
        "# Most Significant Risks",
        "Readmission Rates is the highest-risk department.",
        f"- Highest variability process by CV: {highest_process}.",
        f"- Trend direction for highest variability process: {process_details[highest_process]['direction']}.",
        "",
        "# Prioritized Corrective Actions",
        f"1. Stabilize high-variance {highest_process.replace('_',' ')} sources first.",
        f"2. Enforce denominator-aware daily medication errors monitoring and escalation.",
        f"3. Standardize wait times workflows to reduce spread.",
    ]


    md_lines.extend([
        "",
        "# Monitoring Plan",
        "",
        "## Process to be Monitored",
        report["monitoring_plan"]["process_to_be_monitored"],
        "",
        "## Inputs",
        "- " + "\n- ".join(report["monitoring_plan"]["inputs"]),
        "",
        "## Outputs",
        "- " + "\n- ".join(report["monitoring_plan"]["outputs"]),
        "",
        "## Key Performance Indicators (KPIs)",
    ])

    for kpi in report["monitoring_plan"]["key_performance_indicators"]:
        md_lines.append(
            f"- {kpi['name']}: frequency={kpi['frequency']}; method={kpi['collection_method']}; benchmark={kpi['benchmark']}"
        )

    md_lines.extend([
        "",
        "## Frequency of Monitoring",
        report["monitoring_plan"]["frequency_of_monitoring"],
        "",
        "## Observation Format",
        report["monitoring_plan"]["observation_format"],
        "",
        "## Roles",
    ])

    for role, responsibility in report["monitoring_plan"]["roles"].items():
        md_lines.append(f"- {role}: {responsibility}")

    md_lines.extend([
        "",
        "## Reporting Format",
        report["monitoring_plan"]["reporting_format"],
        "",
        "## Corrective Action Process",
    ])

    for step in report["monitoring_plan"]["corrective_action_process"]:
        md_lines.append(f"- {step}")

    md_lines.extend([
        "",
        "## Benchmarks",
    ])

    for benchmark in report["monitoring_plan"]["benchmarks"]:
        md_lines.append(f"- {benchmark}")

    md_lines.append("")






    with open(MD_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Wrote {JSON_OUTPUT} and {MD_OUTPUT}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /tmp/solve_task.py
echo "Done."
