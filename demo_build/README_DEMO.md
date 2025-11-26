# Fortress Director Demo Build

This folder contains the one-command demo build workflow.

## Quickstart

### Linux / macOS

```bash
./demo_build/run_demo.sh
```

### Windows (PowerShell 7+)

```powershell
.\demo_build\run_demo.ps1
```

Both commands perform the following steps automatically:

1. Create/refresh a Python virtual environment under `demo_build/.venv`.
2. Install `requirements.txt`.
3. Detect Ollama (warn if missing) and run `scripts/download_models.sh`.
4. Install UI dependencies (`npm install`) and build the static bundle into `demo_build/ui_dist/`.
5. Start `uvicorn fortress_director.api:app --port 8000`.
6. Open the default browser to `http://localhost:8000/`.

## Demo config

Runtime toggles live in `demo_config.yaml`. The backend automatically loads it on startup and switches to demo-safe defaults (fallback LLMs, short timeouts, bounded trace sizes, deterministic NPC pacing, etc.). Adjust values here before building the installer.
