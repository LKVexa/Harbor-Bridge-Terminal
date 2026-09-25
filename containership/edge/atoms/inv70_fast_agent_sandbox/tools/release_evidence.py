"""Machine-readable production release acceptance evidence (C090).

python -m inv70_fast_agent_sandbox.tools.release_evidence [--out RELEASE_EVIDENCE.json] [--require-wasm]

Runs every test module, records pass/fail/skip per module with skip reasons,
content digests of every source/doc/config file, the effective config digests
per environment, the dependency pins, the perf baseline digest and the
remediation status of every requirement, then computes a release verdict.
A skip in a *required* suite, any failure, any BLOCKED item or any P0 item not
VERIFIED yields verdict NOT_ACCEPTED (exit 1).  Tampering is detectable: the
file carries a digest over its own canonical body.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import platform
import sys
import time
import unittest

from .. import __version__
from ..config import ENVIRONMENTS, digest, resolve
from .check_lock import LOCK, problems
from .remediation_status import S

ROOT = pathlib.Path(__file__).resolve().parents[1]
P0 = {"C009", "C010", "C019", "C020", "C023", "C025", "C030", "C031", "C037", "C044", "C045", "C048", "C049",
      "C054", "C058", "C072", "C073", "C083", "C085", "C090", "C094", "C097"}
REQUIRED_NO_SKIP = {"test_runtime", "test_security", "test_resilience", "test_config", "test_semantics",
                    "test_telemetry", "test_integration", "test_fuzz", "test_governance"}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_tests(require_wasm: bool):
    tests_dir = ROOT / "tests"
    sys.path.insert(0, str(tests_dir))
    os.environ["INV70_EVIDENCE_RUN"] = "1"
    if require_wasm:
        os.environ["INV70_REQUIRE_WASM"] = "1"
    out = {}
    for f in sorted(tests_dir.glob("test_*.py")):
        mod = f.stem
        suite = unittest.defaultTestLoader.loadTestsFromName(mod)
        res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        out[mod] = {"run": res.testsRun, "failures": len(res.failures), "errors": len(res.errors),
                    "skipped": len(res.skipped), "skip_reasons": sorted({r for _, r in res.skipped}),
                    "passed": res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)}
    return out


def build(require_wasm: bool = False):
    tests = run_tests(require_wasm)
    files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(ROOT.rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts and p.name != "RELEASE_EVIDENCE.json"}
    items = {cid: {"status": st, "implementation": impl, "tests": t, "remaining_gap": gap}
             for cid, (st, impl, t, gap) in S.items()}
    reasons = []
    for m, r in tests.items():
        if r["failures"] or r["errors"]:
            reasons.append(f"{m}: {r['failures']} failures / {r['errors']} errors")
        if m in REQUIRED_NO_SKIP and r["skipped"]:
            reasons.append(f"{m}: {r['skipped']} skipped in a required suite")
    if require_wasm and tests.get("test_wasm", {}).get("skipped"):
        reasons.append("wasm engine tests skipped under --require-wasm")
    for cid, it in items.items():
        if it["status"] == "BLOCKED":
            reasons.append(f"{cid} BLOCKED")
        elif cid.split("-")[-1] in P0 and it["status"] != "VERIFIED":
            reasons.append(f"{cid} is P0 and {it['status']}")
    lock_problems = problems(LOCK.read_text())
    reasons += [f"lock: {p}" for p in lock_problems]
    body = {
        "schema": "inv70.release-evidence/1",
        "component": "INV-70", "release": __version__,
        "source_revision": os.environ.get("INV70_SOURCE_REVISION", "unrecorded"),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(), "machine": platform.machine()},
        "dependencies": {"wasm.lock": LOCK.read_text().strip().splitlines()[-1], "lock_problems": lock_problems,
                         "pk_core": "absent"},
        "config_digests": {env: digest(resolve(env)[0]) for env in ENVIRONMENTS},
        "perf_baseline_sha256": sha(ROOT / "perf" / "baseline.json"),
        "tests": tests,
        "requirements": items,
        "counts": {k: sum(1 for i in items.values() if i["status"] == k) for k in ("VERIFIED", "PARTIAL", "BLOCKED")},
        "file_digests": files,
        "verdict": "ACCEPTED" if not reasons else "NOT_ACCEPTED",
        "verdict_reasons": reasons,
    }
    body["self_digest"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def verify(doc: dict) -> bool:
    d = dict(doc)
    claimed = d.pop("self_digest", None)
    return claimed == hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "RELEASE_EVIDENCE.json"))
    ap.add_argument("--require-wasm", action="store_true")
    a = ap.parse_args(argv)
    doc = build(a.require_wasm)
    pathlib.Path(a.out).write_text(json.dumps(doc, indent=2, sort_keys=True))
    print(json.dumps({k: doc[k] for k in ("release", "verdict", "counts")}, indent=2))
    for r in doc["verdict_reasons"]:
        print(" -", r)
    return 0 if doc["verdict"] == "ACCEPTED" else 1


if __name__ == "__main__":
    sys.exit(main())
