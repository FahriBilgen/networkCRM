#!/usr/bin/env python3
"""Validate that key docs stay aligned with the roadmap."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

EXPECTATIONS: Dict[str, List[str]] = {
    "docs/current_state_baseline.md": [
        "World State",
        "StateStore",
        "Metrics",
    ],
    "docs/theme_packages.md": [
        "theme_schema.json",
        "Theme validate",
        "Simulate",
    ],
    "docs/player_view_summary.md": [
        "player_view",
        "metrics_panel",
        "guardrail_notes",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check docs for required sections/keywords.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs/maintenance"),
        help="Where to store the docs check summary (default: runs/maintenance).",
    )
    return parser.parse_args()


def check_file(path: Path, keywords: List[str]) -> Dict[str, object]:
    if not path.exists():
        return {"status": "missing", "missing_keywords": keywords}
    content = path.read_text(encoding="utf-8")
    missing = [kw for kw in keywords if kw not in content]
    status = "ok" if not missing else "keywords_missing"
    return {"status": status, "missing_keywords": missing}


def main() -> None:
    args = parse_args()
    project_root = Path(__file__).resolve().parent.parent
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs": {},
    }
    overall_ok = True
    for relative, keywords in EXPECTATIONS.items():
        result = check_file(project_root / relative, keywords)
        report["docs"][relative] = result
        if result["status"] != "ok":
            overall_ok = False

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = args.output_dir / f"docs_check_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if overall_ok:
        print(f"Docs check passed (details in {out_path})")
    else:
        print(f"Docs check found issues (see {out_path})")


if __name__ == "__main__":
    main()
