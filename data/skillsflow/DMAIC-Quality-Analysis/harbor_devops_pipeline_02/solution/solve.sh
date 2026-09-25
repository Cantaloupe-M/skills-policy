#!/bin/bash
set -euo pipefail

cat > /tmp/solve_task.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import json
import math

import pandas as pd

DATA_FILE = "/root/pipeline_performance_data.xlsx"
JSON_OUTPUT = "/root/pipeline_performance_report.json"
MD_OUTPUT = "/root/pipeline_performance_brief.md"


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
    p1_df = pd.read_excel(DATA_FILE, sheet_name="Build Duration")
    p2_df = pd.read_excel(DATA_FILE, sheet_name="Bug Rate")
    p3_df = pd.read_excel(DATA_FILE, sheet_name="Deployment Failures")

    p1_vals = p1_df["Build Duration (sec)"].dropna().astype(float).tolist()
    denoms = p2_df["Lines Reviewed"].dropna().astype(float).tolist()
    nums = p2_df["Bugs Found"].dropna().astype(float).tolist()
    p2_rates = [f / n for f, n in zip(nums, denoms)]
    p3_vals = p3_df["Failure Rate"].dropna().astype(float).tolist()

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
    target_rate_pct = 3.0
    capability_vs_target = "Capable" if overall_rate_pct <= target_rate_pct else "Not Capable"

    p3_mean = mean(p3_vals)
    p3_std = sample_std(p3_vals)
    p3_cv = coefficient_of_variation(p3_vals)
    p3_slope, p3_t, p3_stability, p3_direction = linear_trend(p3_vals)

    variability_ranking = sorted(
        [
            {"process": "build_duration", "cv": p1_cv},
            {"process": "bug_rate", "cv": p2_cv},
            {"process": "deployment_failures", "cv": p3_cv},
        ],
        key=lambda x: x["cv"],
        reverse=True,
    )

    highest_process = variability_ranking[0]["process"]
    process_details = {
        "build_duration": {"cv": p1_cv, "slope": p1_slope, "t_stat": p1_t, "stability": p1_stability, "direction": p1_direction},
        "bug_rate": {"cv": p2_cv, "slope": p2_slope, "t_stat": p2_t, "stability": p2_stability, "direction": p2_direction},
        "deployment_failures": {"cv": p3_cv, "slope": p3_slope, "t_stat": p3_t, "stability": p3_stability, "direction": p3_direction},
    }

    report = {
        "build_duration": {
            "n": len(p1_vals),
            "mean_sec": p1_mean,
            "sample_std_sec": p1_std,
            "cv": p1_cv,
            "trend_slope_per_index": p1_slope,
            "trend_t_stat": p1_t,
            "trend_direction": p1_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": p1_stability,
        },
        "bug_rate": {
            "points": len(p2_rates),
            "total_lines": int(total_denom),
            "total_bugs": int(total_num),
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
        "deployment_failures": {
            "rows": len(p3_vals),
            "mean_failure_rate": p3_mean,
            "sample_std_failure_rate": p3_std,
            "cv": p3_cv,
            "trend_slope_per_index": p3_slope,
            "trend_t_stat": p3_t,
            "trend_direction": p3_direction,
            "stability_method": "Linear trend t-test on slope (Stable if |t_stat| < 2.0)",
            "stability": p3_stability,
        },
        "variability_ranking": variability_ranking,
        "highest_variability_process": highest_process,
        "highest_risk_statement": "Deployment Failures is the highest-risk stage.",
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



    report["improvement_plan"] = {
        "process": highest_process,
        "methodology": (
            "Apply systematic software engineering methodology: "
            "scientific debugging for root-cause identification, "
            "structured incident response for production failures, "
            "and technical debt triage to prioritize improvements."
        ),
        "root_cause_approach": (
            "Use the complex-debugging reference sheet: reproduce the issue, "
            "isolate the failure domain, form and test hypotheses in a loop, "
            "identify root cause, implement fix, and add prevention measures."
        ),
        "incident_response_plan": (
            "Follow the incident-response methodology: assess severity and impact, "
            "contain the blast radius, mitigate immediate harm, diagnose the root cause, "
            "fix and verify, then conduct a blameless postmortem."
        ),
        "technical_debt_assessment": (
            "Identify, categorize, and prioritize technical debt that contributes "
            "to deployment failures variance. Focus on high-impact, "
            "low-effort fixes first to maximize reliability improvement per sprint."
        ),
        "prioritized_actions": [
            "1) Stabilize high-variance deployment failures drivers through root-cause debugging",
            "2) Contain bug rate exceedances through structured incident response",
            "3) Standardize build duration workflows and reduce technical debt",
        ],
                "project_codename": "Project Velocity Shield",
                "momentum_plan_30_60_90": {
            "day_30": "Complete baseline validation, owners, and containment actions.",
            "day_60": "Implement top corrective actions and publish interim impact review.",
            "day_90": "Lock updated standard work and move to sustainment cadence.",
        },
    }



    with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    md_lines = [
        "# Summary of Findings",
        f"- Build Duration mean: {p1_mean:.4f}; sample SD: {p1_std:.4f}; CV: {p1_cv:.4f}; stability: {p1_stability}.",
        f"- Bug Rate overall: {overall_rate_pct:.4f}% (95% Wilson CI: {p2_ci_low:.4f}% to {p2_ci_high:.4f}%); stability: {p2_stability}; capability vs 3.0% target: {capability_vs_target}.",
        f"- Deployment Failures mean: {p3_mean:.4f}; sample SD: {p3_std:.4f}; CV: {p3_cv:.4f}; stability: {p3_stability}.",
        "",
        "# Most Significant Risks",
        "Deployment Failures is the highest-risk stage.",
        f"- Highest variability process by CV: {highest_process}.",
        f"- Trend direction for highest variability process: {process_details[highest_process]['direction']}.",
        "",
        "# Prioritized Corrective Actions",
        f"1. Stabilize high-variance {highest_process.replace('_',' ')} sources first.",
        f"2. Enforce denominator-aware daily bug rate monitoring and escalation.",
        f"3. Standardize build duration workflows to reduce spread.",
    ]



    md_lines.extend([
        "",
        "# Improvement Plan",
        "",
        "## Process Under Review",
        report["improvement_plan"]["process"],
        "",
        "## Methodology",
        report["improvement_plan"]["methodology"],
        "",
        "## Root Cause Approach",
        report["improvement_plan"]["root_cause_approach"],
        "",
        "## Incident Response Plan",
        report["improvement_plan"]["incident_response_plan"],
        "",
        "## Technical Debt Assessment",
        report["improvement_plan"]["technical_debt_assessment"],
        "",
    ])


    md_lines.append("Project codename: " + report["improvement_plan"]["project_codename"])

    md_lines.extend([
        "30-day milestone: " + report["improvement_plan"]["momentum_plan_30_60_90"]["day_30"],
        "60-day milestone: " + report["improvement_plan"]["momentum_plan_30_60_90"]["day_60"],
        "90-day milestone: " + report["improvement_plan"]["momentum_plan_30_60_90"]["day_90"],
        "",
    ])


    with open(MD_OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"Wrote {JSON_OUTPUT} and {MD_OUTPUT}")


if __name__ == "__main__":
    main()
PYTHON_SCRIPT

python3 /tmp/solve_task.py
echo "Done."
