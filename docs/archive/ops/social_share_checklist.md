# Social Share Checklist

Owner: Live Ops / Community Â· Updated: 2025-11-08

## Pre-flight

1. Run `fortress_director/scripts/cli.py share_card --json` and ensure `share_card.ready` is true.
2. Verify the latest turn JSON exists under `runs/latest_run/turn_*.json` (needed for telemetry annotations).
3. Install Playwright once on operators' machines: `npm i -g playwright && playwright install chromium`.

## Capture Pipeline

```bash
python tools/share_card_pipeline.py \
  --run-dir runs/latest_run \
  --discord-webhook <URL> \
  --partner-webhook <URL> \
  --image-base-url https://cdn.example.com/share_cards
```

What the script does:

- Loads `player_view.meta_progression.share_card` (falls back to the last turn JSON if `runs/latest/player_view.json` is absent).
- Writes artifacts to `runs/share_cards/<timestamp>/` (`share_card.json`, `recap.html`, `summary.txt`, optional `recap.png`).
- Generates `runs/share_cards/latest.txt` so community managers can grab the hook + metrics quickly.
- Tries to screenshot `recap.html` via Playwright (skipped if `--skip-screenshot` or `npx` is missing). WebP conversion happens when `cwebp` is installed.
- Posts payloads to any provided webhooks (`discord` hero channel, `partner` review channel) with `{summary, story_hook, metrics, achievements, image_url}`.
- Appends an entry to `runs/share_cards/share_log.jsonl` and annotates the latest turn telemetry with `telemetry.share_pipeline` so watchdog/KPI scripts can count posts.

Use `--dry-run` during smoke tests to avoid hitting webhooks while still producing the artifacts/log entry.

## Webhook + Approval Table

| Channel            | Purpose                | Rate Limit | Approval Window |
|--------------------|------------------------|-----------:|-----------------|
| `discord_webhook`  | Player-facing hero card | 5/min      | Ops on-call     |
| `partner_webhook`  | Studio / BizDev review  | 30/min     | Studio producer |

- Keep a thumbnail reference for each post inside the JIRA ticket for that beat.
- If either webhook returns `failed`, re-run with `--note "retry after ..."`. The share log keeps a history for audits.

## Weekly Smoke Test

1. Run `python tools/share_card_pipeline.py --skip-screenshot --dry-run --note smoke-test`.
2. Attach the generated `summary.txt` to the latest entry in `history/ui_playtests.md` under â€œShare pipelineâ€.
3. Capture any Playwright errors; file bugs in `ops/social_share` if screenshots fail two weeks in a row.

