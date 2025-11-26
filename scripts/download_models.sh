#!/usr/bin/env bash
# Download the LLM models required by Fortress Director.

set -euo pipefail

echo "Pulling recommended Ollama models..."
ollama pull mistral:latest
ollama pull qwen2:1.5b
ollama pull phi3:mini

echo "Model downloads complete."
