# SDK Getting Started

The SDK CLI lives in `fortress_director/sdk/cli.py` and is meant for designers and partners
who need quick scaffolding + linting without diving into the full orchestrator.

## Installation

```
python -m fortress_director.sdk.cli --help
```

Run commands from the repo root so relative paths (e.g., `prompts/*.txt`) resolve correctly.

## Commands

### Theme Init

```
python -m fortress_director.sdk.cli theme init themes/my_theme.json --id my_theme --label "Ice Siege"
```

Creates a JSON skeleton mirroring `themes/theme_schema.json`. Edit prompt/asset overrides to taste.

### Prompt Lint

```
python -m fortress_director.sdk.cli prompt-lint prompts/event_prompt.txt prompts/judge_prompt.txt
```

Checks that each prompt exists, is under 6k characters, and has balanced braces (useful when editing with design tools).

### Safe Function Mock

```
python -m fortress_director.sdk.cli safe-function --payload '{"name":"adjust_metric","kwargs":{"metric":"morale","delta":3}}'
```

Validates the payload against the real registry. Add `--run` to execute against a temporary world state or `--theme siege_default` to seed theme overrides before validation.

## Creator Manifest API

- The server exposes `GET /creator/v1/manifest` for a versioned list of themes and safe-function definitions. The payload follows `creator_portal/manifest.schema.json`.
- Additional slices live under `GET /creator/v1/themes`, `/creator/v1/safe-functions`, and `/creator/v1/gallery` (community submissions mock).
- For static validation, run:
  ```bash
  # manifest endpoint retired; await new schema path in docs/demo_overview.md
  ```
  or import `creator_portal.manifest.build_manifest()` inside tooling scripts.
