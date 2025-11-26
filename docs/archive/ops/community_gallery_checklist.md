# Community Gallery Ops Checklist

Owner: Platform / Community Review · Updated: 2025-11-08

## 1. Intake

1. Ensure every submission includes:
   - Repository URL + commit hash.
   - Declared license (CC-BY, custom partner grant, etc.).
   - Contact info for takedown notices.
2. Drop the payload into `creator_portal/gallery_catalog.json` only after the items below pass.

## 2. Security Review

| Step | Tooling | Notes |
| ---- | ------- | ----- |
| Static scan | `scripts/scan_submission.sh <repo>` | Verifies JSON/asset payloads contain no binaries or scripts. |
| Safe function audit | `python fortress_director/sdk/cli.py safe-function --payload ... --run` | Confirm every custom safe function is whitelisted or stubbed. |
| Telemetry guardrails | Inspect `telemetry.share_pipeline` for the submission to ensure no PII is logged. |

## 3. Copyright & IP

1. Confirm art/audio/voice assets are either first-party or accompanied by license text.
2. For NPC kits and story packs, search the text with the `ops/text_similarity.py` helper to catch scraped lore.
3. Record approvals in `history/community_reviews.md` with reviewer, date, and linked evidence.

## 4. Publishing Steps

1. Update `creator_portal/gallery_catalog.json` with:
   - `status`: `approved`, `in-review`, or `needs-ip-review`.
   - `review` block (`safety`, `copyright`, `timestamp`).
2. Run `python tools/publish_autoscale_metrics.py --dry-run` to ensure perf watchdog artifacts exist for the run (gallery metrics piggyback on the same report).
3. Ping `#ops-liveops` with the new entry and include a link to `fortress_director/demo/web/public/community_gallery.html` for visual QA.

## 5. Weekly Maintenance

- Smoke test the gallery UI by opening `/demo/web/public/community_gallery.html` in the staging deployment.
- Archive submissions older than 60 days that remain `needs-ip-review` (move to `history/community_archive.md`).
- Re-run copyright scans if a repository URL changes.
