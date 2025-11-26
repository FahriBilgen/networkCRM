#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/demo_build/.venv"
UI_DIR="$ROOT_DIR/fortress_director/demo/web"
START_URL="http://localhost:8000/"

info() {
  printf "\n[demo] %s\n" "$*"
}

ensure_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo ""
  fi
}

PYTHON_BIN="$(ensure_python)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Python is required but not installed." >&2
  exit 1
fi

info "Creating virtual environment at $VENV_DIR"
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

info "Installing Python dependencies"
python -m pip install --upgrade pip >/dev/null
pip install -r "$ROOT_DIR/requirements.txt"

if command -v ollama >/dev/null 2>&1; then
  info "Ollama detected. Running health check..."
  if ! ollama list >/dev/null 2>&1; then
    echo "Warning: Ollama is installed but unreachable. Demo will rely on scripted fallbacks." >&2
  fi
else
  echo "Warning: Ollama is not installed. Demo will use scripted fallbacks." >&2
fi

MODEL_SCRIPT="$ROOT_DIR/scripts/download_models.sh"
if [[ -x "$MODEL_SCRIPT" ]]; then
  info "Ensuring demo models are available"
  bash "$MODEL_SCRIPT"
else
  echo "Warning: $MODEL_SCRIPT is missing or not executable; skipping model download." >&2
fi

if [[ ! -d "$UI_DIR" ]]; then
  echo "UI directory $UI_DIR not found." >&2
  exit 1
fi

info "Installing UI dependencies"
pushd "$UI_DIR" >/dev/null
npm install
info "Building UI bundle"
npm run build
# If the build produced a local `dist` directory (older configs), copy it
if [[ -d "dist" ]]; then
  info "Copying local dist to demo_build/ui_dist"
  mkdir -p "$ROOT_DIR/demo_build/ui_dist"
  cp -r dist/* "$ROOT_DIR/demo_build/ui_dist/"
fi
popd >/dev/null

UVICORN_BIN="$(command -v uvicorn || true)"
if [[ -z "$UVICORN_BIN" ]]; then
  UVICORN_BIN="$VENV_DIR/bin/uvicorn"
fi
if [[ ! -x "$UVICORN_BIN" ]]; then
  echo "uvicorn not found. Ensure it is installed in the virtual environment." >&2
  exit 1
fi

cleanup() {
  if [[ -n "${UVICORN_PID:-}" ]]; then
    kill "$UVICORN_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

info "Starting backend server (Ctrl+C to stop)"
"$UVICORN_BIN" fortress_director.api:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

sleep 2
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$START_URL" >/dev/null 2>&1 || true
else
  python - <<PY
import webbrowser
webbrowser.open("$START_URL")
PY
fi

wait "$UVICORN_PID"
