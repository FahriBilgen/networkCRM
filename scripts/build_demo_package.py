"""Build a distributable ZIP of the demo.

This collects the demo_build folder, the UI distribution (demo_build/ui_dist),
any run wrappers, and minimal README content into a single zip archive.
The script purposely excludes virtual environments and node_modules.
"""

import sys
from pathlib import Path
import zipfile
import time

ROOT = Path(__file__).resolve().parents[1]
DEMO_BUILD = ROOT / "demo_build"
OUT_DIR = ROOT / "release"

EXCLUDE_NAMES = {
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "ui_dist/node_modules",
}


def should_exclude(p: Path) -> bool:
    parts = set(p.parts)
    return any(ex in parts for ex in EXCLUDE_NAMES)


def build_zip():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%dT%H%M%SZ")
    out_name = f"fortress_director_demo_{timestamp}.zip"
    out_path = OUT_DIR / out_name

    print(f"Creating demo package at {out_path}")
    with zipfile.ZipFile(
        out_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zf:
        if DEMO_BUILD.exists():
            for p in DEMO_BUILD.rglob("*"):
                if p.is_dir():
                    continue
                if should_exclude(p):
                    continue
                rel = p.relative_to(ROOT)
                zf.write(p, arcname=str(rel))
        else:
            print("demo_build/ not found; aborting.")
            return 1

        # include top-level README; demo_build scripts are already included
        # by walking the demo_build/ tree so don't add them twice.
        readme = ROOT / "README_DEMO.md"
        if readme.exists() and readme.is_file():
            zf.write(readme, arcname=str(readme.relative_to(ROOT)))

    print("Package created:", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(build_zip())
