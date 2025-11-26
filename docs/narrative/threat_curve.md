# Threat Curve Whitepaper

## Threat Scoring Formula

Each turn produces a `ThreatSnapshot` computed deterministically from the current
`GameState`. The weighted formula is:

```
threat_score =
  base_threat * w1
+ escalation * w2
+ (100 - morale) * w3
+ (50 - resources) * w4
+ recent_hostility * w5
```

Default weights (`w1`…`w5`) are:

| Component         | Weight |
| ----------------- | ------ |
| base_threat       | 0.45   |
| escalation        | 0.75   |
| morale gap        | 0.60   |
| resource gap      | 0.50   |
| recent hostility  | 1.20   |

Base threat is derived from the current `DemoSpec` (fallback: first metric
reading). Escalation grows using a softened power curve
`min(cap, rate * turn^curve)` with defaults `rate=1.4`, `curve=1.1`, `cap=75`.
Recent hostility counts combat safe-function calls (window of four turns); each
entry contributes `max(0, base - index * decay)` with `base=4`, `decay=0.8`.
If there is no structured combat history the model scans recent textual events
for aggression keywords (`attack`, `sabotage`, `breach`, etc.).

Final scores are clamped to `[0, 100]` for UI readability while preserving the
relative pressure between turns.

## Phase Thresholds

Threat phases drive prompt weightings, planner limits, and UI cues.

| Threat Score | Phase     | Behavioral Notes                       |
| ------------ | --------- | -------------------------------------- |
| `< 20`       | calm      | exploration, scouting, soft logistics  |
| `20–39.99`   | rising    | mixed scouting + fortification         |
| `40–64.99`   | peak      | heavy combat, emergency repairs        |
| `>= 65`      | collapse  | retreat, last stands, endgame triggers |

The `EndgameDetector` activates when the phase is `collapse` **and** morale
(`25`), resources (`20`), or enemy marker counts (default `3`) breach the
thresholds. A triggered endgame clamps the planner to two calls and forces the
Director to produce exactly two options (heroic + desperate fallback).

## Event Curve Buckets

`EventCurve` deterministically emits a thematic seed each turn. The phase and
threat score bias the cursor, preventing streaky repeats. Default seeds are:

- **calm** – `minor_scouting`, `supply_drop`, `weather_shift`
- **rising** – `sabotage`, `scouting_party`, `reinforcement_arrival`
- **peak** – `enemy_assault`, `fire_breakout`, `breach_warning`
- **collapse** – `final_breach`, `last_reserve`, `evacuation_crisis`

Event seeds are injected into both Director and World Renderer prompts and also
surface on the UI event log (e.g., `Event: Enemy assault`). The curve is
purely deterministic: only the current snapshot, turn, and map markers
influence the selection, making it safe for offline tests.

## Escalation and UI Integration

- Director prompts show `CURRENT_THREAT_PHASE`, `CURRENT_THREAT_SCORE`, and the
  active event seed. Final-trigger directives inject the exact two option
  guardrail block.
- World Renderer prompts receive the threat phase and event seed so atmosphere
  cues align with the pacing.
- `/api/run_turn` now returns `threat_score`, `threat_phase`, and `event_seed`.
  The HUD exposes a color-coded threat bar and the shell adds a collapse tint
  when the phase reaches `collapse`.
