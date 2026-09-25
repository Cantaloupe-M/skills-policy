You are an Industrial Engineer supporting the Analyze tollgate of a DMAIC project for North Fulfillment Center LLS operations.

Use `/root/Processing_Data.xlsx` as the only data source. The file has daily UPR records and stage/day metadata.

Your task is to produce two outputs:

1) `/root/analyze_tollgate_metrics.json`
2) `/root/analyze_tollgate_brief.md`

## Required analysis rules

- Date range for primary analysis: `2025-01-04` through `2025-03-01` (inclusive).
- Use business days only (Monday-Friday) for ANOVA, regression, t-test, and capability calculations.
- Use `2025-01-04` through `2025-02-21` (inclusive), business days only, for I-MR metrics (Baseline + Define + Measure window).
- Treat `UPR` as the response metric everywhere.
- For regression, use `day_index` (1..n over business-day rows sorted by date) as the sole predictor.

## JSON output requirements

Write `/root/analyze_tollgate_metrics.json` with these top-level keys:

- `source_file`
- `filters`
- `record_counts`
- `charter_metrics`
- `anova_by_weekday`
- `imr_summary`
- `regression_day_index`
- `ttest_vs_target`
- `capability_against_lsl`

Include at least these fields:

- `charter_metrics.baseline_upr` = `3189`
- `charter_metrics.target_upr` = `3400`
- `charter_metrics.current_mean_upr` (computed from business-day primary window)
- `anova_by_weekday.weekday_means` for Monday..Friday
- `anova_by_weekday.p_value`
- `anova_by_weekday.highest_mean_day`
- `anova_by_weekday.lowest_mean_day`
- `imr_summary.points`
- `imr_summary.center_line`
- `imr_summary.ucl`
- `imr_summary.lcl`
- `imr_summary.mr_bar`
- `imr_summary.mr_ucl`
- `regression_day_index.slope`
- `regression_day_index.intercept`
- `regression_day_index.r_value`
- `regression_day_index.p_value`
- `ttest_vs_target.n`
- `ttest_vs_target.mean_upr`
- `ttest_vs_target.t_stat`
- `ttest_vs_target.p_value`
- `ttest_vs_target.ci95_low`
- `ttest_vs_target.ci95_high`
- `ttest_vs_target.decision` (`reject_h0` or `fail_to_reject_h0`)
- `capability_against_lsl.lsl` = `3400`
- `capability_against_lsl.std_dev_sample`
- `capability_against_lsl.cpk_lower`

## Markdown brief requirements

Write `/root/analyze_tollgate_brief.md` with these exact section headers:

- `# DMAIC Analyze Tollgate Brief`
- `## Project Charter`
- `## Statistical Analysis`
- `## A3 Summary`
- `## Timeline and Next Steps`

Under Statistical Analysis, include named subsections for:

- One-Way ANOVA
- I-MR Control Chart
- Linear Regression (UPR ~ day_index)
- One-Sample t-Test vs 3400
- Process Capability

Also include:

- At least two operational impacts selected from:
  - increased manual intervention
  - delayed downstream workflows
  - missed handoffs
  - higher operating expenses
- Timeline dates:
  - Define start `2025-02-08`
  - Measure start `2025-02-15`
  - Analyze start `2025-02-22`
- Two next-step actions, each with an owner and a due date in March 2025.


