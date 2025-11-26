# UI Accessibility & Playtest Targets

## Accessibility Goals

- **Contrast:** All HUD text, chips, and buttons must meet WCAG 2.1 AA (4.5:1) with a default dark palette and an optional high-contrast palette (>=7:1). Verify using the browser devtools contrast checker on the default and `High Contrast` toggle.
- **Typography:** Interactive controls render at >=16px in default mode and >=18px when `Large Text` is enabled. Body copy must never drop below 14px to keep tooltips readable.
- **Color Safety:** Status pills and markers rely on both color and text labels (e.g., `Threat: High`, severity tags) to remain legible for color-impaired players.
- **Motion:** All animations are decorative. Respect `prefers-reduced-motion` by disabling transitions/pulses when the media query is active.
- **Live Regions:** Telemetry/map diff feeds expose `aria-live="polite"` so screen readers hear high-value updates without stealing focus.

## Rapid Playtest Protocol

1. **Setup:** Start the FastAPI server, open `/ui/`, and ensure telemetry SSE is connected (status feed updates when turns run).
2. **Tutorial Sweep:** Run three automated turns (`Play Turn (default)`), capture screenshots of the HUD and tutorial overlay. Confirm guidance text updates across turns.
3. **Manual Choice Test:** Pick a branch from the options list and verify the map activity feed pulses the affected layers/markers after the turn resolves.
4. **Story Pressure Panels:** Inspect the NPC Loyalty, Resource Pressure, and Event Chain cards. Confirm loyalty statuses/roles sync with the latest turn, resource pills flag low supplies, and the event chain lists both recent and scheduled beats.
5. **Meta Progression:** Verify the Meta Unlocks/Achievements lists and Share Card box update after each turn; use the `Copy Summary` button to ensure the clipboard text matches the on-screen card when status is Ready.
6. **Accessibility Pass:** Toggle `High Contrast` and `Large Text` while a turn summary is visible. Confirm controls retain focus styling and the HUD remains readable without horizontal scroll on a 1280px-wide viewport.
7. **Regression Log:** Record findings (pass/fail, screenshots, notes) in `history/ui_playtests.md` or the sprint tracking doc so future roadmap phases inherit the baselines.

> This checklist is intentionally lightweight so it can run alongside weekly regression bundles. Extend it with scenario-specific tasks whenever a new theme or map-safe-function variant ships.
