# Localization & UI QA Guide

Last updated: 2025-11-08  
Owner: Experience Engineering

## 1. Pipeline Overview

1. **State â†’ Player View:** `StateServices` injects `player_view.localization` (locale, fallback chain, strings).
2. **UI Preview:** `fortress_director/demo/web/public/localization_preview.html` consumes that payload to render HUD text, share-card labels, and metadata for QA.
3. **Phrasebooks & Theme Strings:** Phrasebooks live in `localization/phrasebook/*.yaml`; theme-specific strings (names, banners) live in `themes/<theme>/strings.json`.

## 2. Running the Preview

1. Generate a fresh `player_view.json` (e.g., `python fortress_director/scripts/cli.py run_turn --theme siege_default`).
2. Open `fortress_director/demo/web/public/localization_preview.html` in a browser (no build step required).
3. Drop the JSON file or click â€œFetch runs/latest/player_view.jsonâ€.
4. Toggle **RTL** or **Low Bandwidth** to verify layout changes without re-running the sim.

## 3. QA Checklist

| Scenario | Steps | Expected Result |
| --- | --- | --- |
| Baseline locale | Load EN snapshot, keep defaults | HUD labels and share card use English strings; locale/fallbacks surface in the status panel. |
| Turkish locale | Load snapshot with `player_view.localization.locale = tr` | HUD labels display Turkish strings, share-card banner uses `Lornhaven'i Koru`. |
| Missing localization | Manually strip the `localization` block from JSON | Preview shows warning banner (`player_view.localization missing`). |
| RTL mode | Click **Toggle RTL** | Layout direction flips (cards align right) without reloading data. |
| Low bandwidth | Click **Toggle Low Bandwidth** | Background darkens, screenshot placeholder hides; text still readable. |
| Share-card ready state | Flip `meta_progression.share_card.ready` to true/false | Status pill swaps between localized ready/pending strings. |

Log defects in `history/ui_playtests.md` and link the JSON sample you used; the preview keeps raw localization data visible for copying into bug reports.

## 4. Adding a New Locale

1. Create `localization/phrasebook/<locale>.yaml` with `locale`, `fallbacks`, and `strings`.
2. Add theme-specific overrides to `themes/<theme>/strings.json` under `locales.<locale>`.
3. Re-run a turn; verify the new locale via the preview.
4. Update this guide if extra QA steps are needed (e.g., new scripts, fonts).

