# Release Checklist

This checklist extends the roadmap "Sonraki Adimlar" requirements so that every sprint ships with traceable telemetry, dependency/log audits, and doc validations.

## 1. Automation Health (T-5 days)

1. Confirm that the scheduled workflow `.github/workflows/weekly-kpi.yml` succeeded on the latest Monday run. If it failed, rerun with `workflow_dispatch` and attach the resulting artifact to the sprint channel.
2. Manually spot-check KPI output:
   ```bash
   python tools/perf_watchdog.py --turns 3 --random-choice --reset-state --report-dir runs/perf_reports/manual
   python tools/perf_watchdog.py --turns 3 --random-choice --reset-state --live-models --tag live_pilot --report-dir runs/perf_reports/manual
   python tools/kpi_digest.py --report-dir runs/perf_reports/manual --summary-path runs/perf_reports/manual/kpi_summary.md
   ```
   Upload the markdown to the sprint ticket so product/design can see turn durations and storage KPIs.

## 1b. Labs Canary Validation (T-4 days)

1. Check `.github/workflows/labs-canary.yml` in GitHub Actions. The cron (`0 3 * * *`) must be green for the current week; if it failed, trigger `workflow_dispatch` with the "Run workflow" button or via `gh workflow run labs-canary`.
2. Review the generated artifacts:
   - `labs-canary-theme-report` (theme simulate output under `runs/canary`).
   - Pytest summary for `tests/test_safe_functions.py` + `tests/test_safe_function_validation.py`.
3. If the workflow flagged a regression (non-zero exit), re-run locally:
   ```bash
   python fortress_director/scripts/cli.py theme simulate themes/siege_default.json --turns 2 --random-choices --offline --output runs/canary/manual_report.json
   pytest tests/test_safe_functions.py tests/test_safe_function_validation.py -q
   ```
   Attach the rerun artifacts to the release issue and note whether the failure reproduces.

## 2. Dependency & Log Audit (T-3 days)

1. Run `python tools/dependency_log_audit.py --output runs/maintenance/dependency_audit.json`.
2. Review the diff versus the previous audit (same folder) and file issues for any newly introduced packages or WARN-level loggers.
3. Attach the JSON (or condensed markdown) to the release doc; this satisfies the roadmap requirement to manually inspect dependency/log scripts every sprint.

## 3. Documentation Consistency (T-2 days)

1. Execute `python tools/docs_consistency_check.py --out runs/maintenance/docs_consistency.md`.
2. Compare findings with `docs/current_state_baseline.md`, `docs/theme_packages.md`, and `docs/theme_prompt_backlog.md`; resolve mismatches or record TODOs.
3. Update `docs/theme_prompt_backlog.md` and `docs/story_packs.md` with any late changes before RC tagging.

## 4. Regression & Telemetry Sign-off (T-1 day)

1. Run `python tools/regression_runner.py --tag release_candidate` and archive output under `runs/regressions/release_candidate`.
2. Generate a fresh telemetry slice that references the regression run directory:
   ```bash
   python tools/telemetry_report.py --run runs/regressions/release_candidate --turns 20 --out runs/regressions/release_candidate/kpi.txt
   ```
3. Post the KPI text plus the latest perf watchdog markdown to the release channel; this step replaces the manual "share KPI" reminder in the roadmap.

## 5. Release Day Checklist (T-0)

1. Ensure all artifacts cited above are linked inside the release issue.
2. Validate that `docs/release_checklist.md` has no unchecked steps; if any were skipped, note the reason in the issue before tagging.
3. Tag the release and trigger the deployment pipeline per ops SOP.

