#!/usr/bin/env sh
# GAP-05 release gates (MC49-007). Run from the directory that CONTAINS the package.
set -eu
PKG=gap05_state_replication_consistency_model
export PYTHONDONTWRITEBYTECODE=1
python3 -B -c "import ast,pathlib,sys; [ast.parse(p.read_text(), str(p)) for p in pathlib.Path(sys.argv[1]).rglob('*.py')]" "$PKG"
python3 -B "$PKG/tests/test_model_logic.py"
python3 -B "$PKG/tests/test_component.py"            # pk_core conformance (skips without pk_core)
python3 -B -m unittest discover -s "$PKG/tests/production" -t "$PKG/tests/production"
python3 -B -m "$PKG.production.modelcheck" > /dev/null
python3 -B "$PKG/tools/check_evidence_refs.py" "$PKG"
python3 -B "$PKG/tools/verify_sums.py" "$PKG"
echo "ALL GATES PASSED (unit, property, crash, fuzz-smoke, model-check, evidence refs, checksums)"
