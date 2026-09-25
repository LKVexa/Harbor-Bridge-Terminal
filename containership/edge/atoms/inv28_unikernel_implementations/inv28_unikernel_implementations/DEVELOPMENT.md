# Developer setup (MC-089)

Requirements: CPython 3.10 or newer. Nothing else is needed; pk_core is vendored.

```bash
# from the folder that CONTAINS inv28_unikernel_implementations/
python -B -m inv28_unikernel_implementations.tools.bootstrap      # checks the interpreter, pk_core digests, schemas, MASTER.md
python -B inv28_unikernel_implementations/tests/run_all.py         # full profile
python -B -O inv28_unikernel_implementations/tests/run_all.py      # same profile, optimised mode
python -B -m inv28_unikernel_implementations.tools.check_all       # every local gate lane (what CI runs)
python -B -m inv28_unikernel_implementations.cli demo              # select/refuse/explain against the fixture world
```

Optional tools, used when installed and skipped with a note when not: `ruff` (lint/format, configured in `pyproject.toml`), `mypy` (types, configured in `pyproject.toml`) and `pre-commit` (`.pre-commit-config.yaml`). The stdlib fallbacks (`tools/lint.py`, `tools/sast.py`, `tools/secret_scan.py`) always run.

Installing as a package: `pip install ./inv28_unikernel_implementations`. `pyproject.toml` has no runtime dependencies.
