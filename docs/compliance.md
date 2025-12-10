# Data Privacy & Compliance Checklist

_Last updated: 2025-11-08 — Owner: Platform / Compliance_

## 1. Data Classes

| Category | Examples | Storage Target | Masking Rule |
| --- | --- | --- | --- |
| Player Identifiers | email, account_id, session tokens | `player_view`, telemetry, logs | Hash with SHA256 and drop raw tokens outside secure store. |
| Narrative Content | prompts, NPC dialogue, share_cards | SQLite history + runs/ | Not PII, but redact unreleased theme names during playtests. |
| Operational Metadata | GPU ids, autoscale events | logs/, CloudWatch | No masking required; rotate access keys monthly. |

## 2. Masking Rules

1. **player_view payloads** — apply `mask_player_identifiers(state)` before persisting. Function lives in `fortress_director/utils/privacy.py`.
2. **Logs** — `settings.LOG_SENSITIVE_FIELDS` enumerates keys stripped from integration logs. Extend this list for new safe-function outputs.
3. **Exports** — `tools/telemetry_report.py` must drop `player_email` and `discord_handle` columns when writing CSVs.

## 3. Data Retention

- `runs/` artifacts: keep 30 days. Rotate via nightly cron (`scripts/rotate_runs.sh`).
- `history/turn_X.json`: archive long-term but gzip after 14 days.
- `telemetry.sqlite`: VACUUM weekly; prune rows older than 60 days unless flagged for incidents.

## 4. Access Controls

- Production data lives in the `fortress-prod` resource group. GitHub Actions use federated credentials scoped to read-only buckets.
- Local developers must set `ALLOW_PLAYER_DATA=0` to prevent accidental syncing from production.
- Any manual export requires an entry in `history/compliance_exports.md` with requester, scope, expiry.

## 5. Review Cadence

- Run `tools/dependency_log_audit.py` monthly and attach the output to `docs/release_checklist.md`.
- Before every release candidate, confirm:
  1. `docs/compliance.md` is up to date.
  2. `player_view` schema matches the masking contract.
  3. `.github/workflows/labs-canary.yml` masks secrets (no plaintext webhooks).

This checklist fulfills the Phase G roadmap ask for a privacy/compliance guide tied to player_view + log masking.
