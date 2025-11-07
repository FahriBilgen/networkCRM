# Story Pack Playbook

Date: 2025-11-07  
Owner: Codex assistant

## Repository Layout

Each story pack lives under `themes/` and ships with:

- `<id>.json` — core metadata + overrides (world state, safe functions, prompts).
- `<id>/prompts/*.txt` — optional prompt overrides.
- `docs/story_packs.md` (this file) — onboarding + validation steps.

Designers keep pack assets under version control and use the new sandbox CLI to
validate narrative flow without touching code.

## Creating a Pack

1. Copy `themes/siege_default.json` as template, update `id`, `label`,
   and `description`.
2. Fill out `prompt_overrides`, `world_state_overrides`, and
   `safe_function_overrides` sparingly—only what the theme needs.
3. Run `python fortress_director/cli.py theme validate <id>` to ensure schema
   compliance.
4. Use the sandbox workflow below before requesting engineering review.

## Sandbox Workflow

Designers can simulate a few turns with offline models:

```bash
python fortress_director/cli.py theme sandbox themes/orbital_frontier.json --turns 3
```

This prints per-turn scene snippets, player choices, metric snapshots, and
safe-function usage so writers can iterate quickly.

## Publishing

- Keep a short README per pack (e.g., `themes/<id>/README.md`) describing key
  motifs, unlock conditions, and required assets.
- Update `docs/theme_packages.md` with a short description and links to
  sandbox transcripts.
- Ensure telemetry output (via `tools/telemetry_report.py`) for the pack meets
  performance SLAs before landing changes.
