#!/usr/bin/env python3
"""Simple probe tool to check local Fortress Director API and Ollama.

Usage:
  python tools/probe_ollama.py         # runs both API status and Ollama model list
  python tools/probe_ollama.py --generate phi3:mini "Hello"

This uses only the Python stdlib so it should work inside the project's venv.
"""
from __future__ import annotations

import argparse
import json
import sys
from urllib import error, request
from urllib.parse import urljoin


def http_get(url: str, timeout: float = 10.0) -> object:
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {exc.code} from {url}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Cannot reach {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from {url}: {exc}") from exc


def ollama_generate(
    base: str, model: str, prompt: str, timeout: float = 30.0
) -> object:
    url = urljoin(base if base.endswith("/") else base + "/", "api/generate")
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(
        "utf-8"
    )
    req = request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        raise RuntimeError(f"Ollama HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Cannot reach Ollama at {base}: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--api",
        default="http://127.0.0.1:8000/api/status",
        help="Fortress Director API status URL",
    )
    parser.add_argument(
        "--ollama", default="http://127.0.0.1:11434/", help="Ollama base URL"
    )
    parser.add_argument(
        "--generate",
        nargs=2,
        metavar=("MODEL", "PROMPT"),
        help="Run a quick generate against Ollama",
    )
    args = parser.parse_args()

    try:
        print("-> Querying Fortress Director API status:")
        status = http_get(args.api)
        print(json.dumps(status, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"API status check failed: {exc}", file=sys.stderr)

    try:
        print("\n-> Querying Ollama model list:")
        models = http_get(
            urljoin(
                args.ollama if args.ollama.endswith("/") else args.ollama + "/",
                "v1/models",
            )
        )
        print(json.dumps(models, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"Ollama model list check failed: {exc}", file=sys.stderr)

    if args.generate:
        model, prompt = args.generate
        try:
            print(f"\n-> Probing generate (model={model}):")
            out = ollama_generate(args.ollama, model, prompt)
            print(json.dumps(out, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"Ollama generate failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
