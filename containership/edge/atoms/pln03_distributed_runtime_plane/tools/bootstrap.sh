#!/usr/bin/env sh
# MC-026 deterministic empty-node bootstrap. No network access, no third-party packages.
set -eu
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3,10), sys.version' 
cd "$HERE"
"$PY" -m unittest discover -s tests -p 'test_*.py' -t tests 2>&1 | tail -3
"$PY" audit_repository.py
echo "bootstrap OK: $("$PY" -c 'import pathlib;print(pathlib.Path("VERSION").read_text().strip())')"
