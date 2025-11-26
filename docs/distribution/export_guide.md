**Export Guide: Building the Demo Package**

- **Purpose**: Produce a portable ZIP containing the demo runner, UI distribution, and run wrappers.
- **Command**: `python scripts/build_demo_package.py`
- **Output**: `release/fortress_director_demo_<timestamp>.zip`
- **Contents**:
  - `demo_build/` (scripts and run wrappers)
  - `demo_build/ui_dist/` (production UI build)
  - `README_DEMO.md` and basic run instructions
- **Exclusions**: The packager excludes `node_modules`, virtualenv folders, and other heavy build artifacts.
- **Recommended workflow**:
  1. Run `demo_build/setup_demo.sh` to install deps and build UI.
  2. Run `python scripts/smoke_test_demo.py` to verify the server/UI are up.
  3. Run `python scripts/build_demo_package.py` to create the distributable.
