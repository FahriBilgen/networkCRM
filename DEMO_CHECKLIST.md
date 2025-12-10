**Demo Checklist**
- **Install Python 3.8+**: Create virtual environment with `demo_build/setup_demo.sh` or `demo_build/setup_demo.ps1`.
- **Install UI deps**: `npm install` in `fortress_director/demo/web` (handled by setup scripts).
- **Build UI**: `npm run build` — output placed into `demo_build/ui_dist`.
- **Start Demo**: Run `demo_build/setup_demo.sh` (Linux/macOS) or `demo_build/setup_demo.ps1` (PowerShell).
- **Smoke Test**: `python scripts/smoke_test_demo.py` — verifies backend and UI index.
- **Create Package**: `python scripts/build_demo_package.py` — creates ZIP in `release/`.
- **Distribute**: Share ZIP and `README_DEMO.md` with users; include platform-specific setup notes.
