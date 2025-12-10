# Economy Tuning Table

`tools/resource_balancer.py` consumes this table to flag unsafe economic swings.
Keep this file as the single source of truth for resource guardrails.

- **Min/Max Safe:** Preferred steady-state band for the metric.
- **Delta Warn/Critical:** Max allowed per-turn drop/rise before the script warns.
- **Telemetry Key:** Dotted path inside `player_view` or telemetry snapshots.

<!-- BEGIN BALANCE TABLE -->
| Resource | Telemetry Key | Min Safe | Max Safe | Delta Warn | Delta Critical | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| morale | resources.morale | 45 | 85 | 10 | 18 | Keep morale mid-band; below 40 triggers fallback copy. |
| supplies | resources.supplies.current | 60 | 140 | 20 | 35 | Schedule convoy events if <80 for 3 turns. |
| defenses | metrics.fortitude | 50 | 95 | 12 | 20 | Mirrors wall integrity + safe-function boosts. |
| intel | resources.intel | 30 | 80 | 8 | 15 | Loss of scouts when <30; guardrails kick in. |
| civilians | population.civilians | 400 | 800 | 60 | 120 | Large drops require evac story beats. |
| glitch | metrics.glitch | 5 | 45 | 8 | 15 | Guardrail pressure; >45 triggers auto fallback. |
<!-- END BALANCE TABLE -->

When updating the table:

1. Confirm the telemetry key exists in `player_view`.
2. Re-run `resource_balancer.py --dry-run` with recent snapshots.
3. Mirror threshold changes in the relevant Live Ops plan (Phase F).

## Live Ops Link

- Keep the JSON actions in sync with this table so automated alerts and operator broadcast messages point to the same thresholds.

## Running the Analyzer

Use either the standalone script or the CLI command:

```bash
python tools/resource_balancer.py --player-view runs/latest/player_view.json --fail-on-critical

python fortress_director/scripts/cli.py resource_balance --player-view runs/latest/player_view.json --fail-on-critical
```

Both variants read the table in this document and highlight risky deltas; add `--report-file reports/balance.json` to export structured output for dashboards.

