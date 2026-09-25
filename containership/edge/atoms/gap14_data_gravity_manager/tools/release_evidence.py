"""Release evidence: file digests, SBOM, test report, bench, handshake (G14-P1-26, D06, final bundle).

    python gap14_data_gravity_manager/tools/release_evidence.py --out gap14_data_gravity_manager/evidence

Writes:
  evidence/SBOM.cdx.json          CycloneDX 1.5 SBOM (components: this package, python runtime; no 3rd-party deps)
  evidence/test_report.json       unittest results per module (executed/skipped/failed + skip reasons)
  evidence/release_evidence.json  version, source tree digest, per-file sha256, handshake, test summary
and regenerates MANIFEST.sha256.  Signing of the release artifact is performed by the estate
release signer (not available here); ``signature`` is therefore recorded as null, never faked.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import platform
import sys
import unittest

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
sys.path.insert(0, str(ROOT))
EXCLUDE_DIRS = {"__pycache__", "evidence"}


def files():
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & EXCLUDE_DIRS) and p.name != "MANIFEST.sha256":
            yield p


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.discover(str(PKG / "tests"), top_level_dir=str(ROOT))
    report = {}

    class R(unittest.TextTestResult):
        pass
    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=0, resultclass=R).run(suite)
    report["ran"] = res.testsRun
    report["failures"] = [str(t) for t, _ in res.failures]
    report["errors"] = [str(t) for t, _ in res.errors]
    report["skipped"] = [{"test": str(t), "reason": why} for t, why in res.skipped]
    report["passed"] = res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)
    report["ok"] = res.wasSuccessful()
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    import gap14_data_gravity_manager as g
    from gap14_data_gravity_manager import compat

    digests = {p.relative_to(PKG).as_posix(): sha(p) for p in files()}
    (PKG / "MANIFEST.sha256").write_text("".join(f"{h}  {n}\n" for n, h in digests.items()), encoding="utf-8")
    tree = hashlib.sha256("".join(f"{n}:{h}\n" for n, h in digests.items()).encode()).hexdigest()
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "gap14-data-gravity-manager", "version": g.__version__,
                                       "hashes": [{"alg": "SHA-256", "content": tree}]}},
            "components": [{"type": "platform", "name": "cpython", "version": platform.python_version(),
                            "description": "runtime; supported range >=3.11,<3.14"}],
            "dependencies": [{"ref": "gap14-data-gravity-manager", "dependsOn": []}],
            "properties": [{"name": "gap14:third_party_runtime_dependencies", "value": "0"},
                           {"name": "gap14:optional", "value": "pk_core (external conformance runtime, pinned in compat.PKCORE_PIN)"}]}
    (out / "SBOM.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n")
    tests = run_tests()
    (out / "test_report.json").write_text(json.dumps(tests, indent=2) + "\n")
    ev = {"schema": "PK_GAP14_RELEASE_EVIDENCE/1", "version": g.__version__, "tree_sha256": tree,
          "python": platform.python_version(), "files": digests, "handshake": compat.handshake().as_dict(),
          "tests": {k: tests[k] for k in ("ran", "passed", "ok")} | {"skipped": len(tests["skipped"])},
          "signature": None, "signature_note": "release signing is an estate release-engineering step; not performed here",
          "source_revision": None, "source_revision_note": "no VCS in this build environment; record commit at release"}
    (out / "release_evidence.json").write_text(json.dumps(ev, indent=2) + "\n")
    print(json.dumps(ev["tests"]), tree)
    return 0 if tests["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
