#!/usr/bin/env sh
# Local CI (mirrors .github/workflows/ci.yml). Run from the directory that CONTAINS the package.
set -eu
PKG=inv55_secrets_integration
python3 -B -m compileall -q "$PKG" >/dev/null
python3 -B "$PKG/tools/secret_scan.py" "$PKG"
python3 -B "$PKG/tools/sbom.py" >/dev/null
python3 -B "$PKG/tools/build_status.py"
python3 -B -m unittest discover -s "$PKG/tests"
python3 -B -O "$PKG/tests/test_secrets_primitives.py"
# The production gate is expected to return NO_GO (exit 3) until approvals, real Vault and pk_core exist.
set +e
python3 -B "$PKG/tools/gate.py"
rc=$?
set -e
[ "$rc" -eq 0 ] && echo "gate: GO" || echo "gate: NO_GO (exit $rc) - release blocked, CI itself green"
