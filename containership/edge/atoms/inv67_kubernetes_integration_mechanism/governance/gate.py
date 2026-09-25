"""Executable 68-component production-readiness gate (items 09, 54, 55, 63).

    python -m inv67_kubernetes_integration_mechanism.governance.gate            # local mode
    python -m inv67_kubernetes_integration_mechanism.governance.gate --release  # exit 1 unless GO

Runs the whole test suite in-process (one unittest run, recording every test's
outcome), then for each component checks its artifacts exist (digested), maps
it to requirements and tests through ``docs/requirements.json`` plus direct
test bindings, and emits:

  evidence/test_results.json          every test id -> pass/fail/skip
  evidence/components/NN.json         INV67_EVIDENCE/1 entry per component
  evidence/TRACEABILITY.json          requirement -> items -> tests -> results
  evidence/ACCEPTANCE_BUNDLE.json     hash-chained bundle (+HMAC if key in env)
  evidence/GATE_RESULT.json           verdict and blockers

A component is ``IMPLEMENTED_LOCALLY_VERIFIED`` only if all its artifacts
exist and it has >= 1 bound test and every bound test passed. Its acceptance
gate is ``MET`` only if it also has no open exception. Because EXC-002
(independent review) is open for every component, no acceptance gate can be
MET from this archive — the gate refuses self-acceptance by construction.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import io
import json
import os
import pathlib
import platform
import sys
import time
import unittest

from . import registry

ROOT = registry.ROOT
EV = ROOT / "evidence"

# Direct bindings for components whose evidence is a whole suite or a doc check.
DIRECT = {
    1: ["unit.test_docs.Docs.test_ownership_roles_defined"],
    2: ["unit.test_docs.Docs.test_adr_sections"],
    9: ["unit.test_docs.Docs.test_requirements_link_to_real_tests"],
    23: ["unit.test_docs.Docs.test_threat_model_covers_mitigations"],
    29: ["security.test_adversarial."],
    36: ["fault.test_faults."],
    38: ["unit.test_docs.Docs.test_slo_doc_matches_benchmark"],
    39: ["performance.test_benchmark."],
    46: ["unit.test_docs.Docs.test_telemetry_artifacts"],
    47: ["unit.test_docs.Docs.test_telemetry_artifacts"],
    48: ["contract.test_contracts."],
    49: ["integration.test_end_to_end."],
    51: ["fuzz.test_property."],
    52: ["concurrency.test_races."],
    56: ["unit.test_docs.Docs.test_supported_versions_match_matrix"],
    57: ["unit.test_docs.Docs.test_policies_present"],
    58: ["unit.test_docs.Docs.test_runbooks_complete"],
    59: ["unit.test_docs.Docs.test_runbooks_complete"],
    60: ["unit.test_docs.Docs.test_policies_present"],
    61: ["unit.test_docs.Docs.test_policies_present"],
    62: ["unit.test_docs.Docs.test_exceptions_ledger_valid"],
    64: ["unit.test_release.Release.test_pyproject_metadata"],
    65: ["unit.test_release.Release.test_ci_workflow_runs_gate"],
    66: ["unit.test_release.Release.test_sbom_and_notice"],
    67: ["unit.test_release.Release.test_static_analysis_config"],
    68: ["unit.test_release.Release.test_manifest_detects_tamper_missing_extra"],
}


class _Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes: dict[str, str] = {}

    def addSuccess(self, t):
        super().addSuccess(t)
        self.outcomes[t.id()] = "pass"

    def addFailure(self, t, e):
        super().addFailure(t, e)
        self.outcomes[t.id()] = "fail"

    def addError(self, t, e):
        super().addError(t, e)
        self.outcomes[getattr(t, "id", lambda: str(t))()] = "fail"

    def addSkip(self, t, r):
        super().addSkip(t, r)
        self.outcomes[t.id()] = "skip"


def run_tests() -> dict[str, str]:
    tests = str(ROOT / "tests")
    if tests not in sys.path:
        sys.path.insert(0, tests)
    suite = unittest.defaultTestLoader.discover(tests, pattern="test_*.py", top_level_dir=tests)
    stream = io.StringIO()
    res = unittest.TextTestRunner(stream=stream, resultclass=_Recorder, verbosity=0).run(suite)
    return res.outcomes


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def resolve(test_ref: str, outcomes: dict[str, str]) -> list[tuple[str, str]]:
    if test_ref.endswith("."):
        hits = [(k, v) for k, v in outcomes.items() if k.startswith(test_ref)]
        return hits or [(test_ref + "*", "missing")]
    return [(test_ref, outcomes.get(test_ref, "missing"))]


def evaluate(outcomes: dict[str, str]) -> dict:
    reqs = json.loads((ROOT / "docs/requirements.json").read_text())["requirements"]
    exc = {e["id"]: e for e in json.loads((ROOT / "docs/governance/exceptions.json").read_text())["entries"]}
    owner = json.loads((ROOT / "docs/governance/ownership.json").read_text())["roles"]["primary_owner"] or "unassigned"
    env = {"python": platform.python_version(), "implementation": platform.python_implementation(),
           "platform": platform.platform(), "tool": "governance/gate.py"}
    comps, trace = [], []
    for r in reqs:
        res = [x for t in r["tests"] for x in resolve(t, outcomes)]
        trace.append({"requirement": r["id"], "items": r["items"], "tests": [{"id": i, "result": v} for i, v in res],
                      "status": "present" if res and all(v == "pass" for _, v in res) else "partial"})
    for c in registry.components():
        n = c["item"]
        arts, missing = [], []
        for a in c["artifacts"]:
            p = ROOT / a
            if p.is_file():
                arts.append({"path": a, "sha256": _sha(p)})
            else:
                missing.append(a)
        rids = [r["id"] for r in reqs if n in r["items"]]
        refs = [t for r in reqs if n in r["items"] for t in r["tests"]] + DIRECT.get(n, [])
        tests = sorted(set(x for t in refs for x in resolve(t, outcomes)))
        open_exc = [e for e in c["exceptions"] if e in exc and not (exc[e].get("approver") and exc[e].get("expires"))]
        blockers = [f"{e}: {exc[e]['text']}" for e in open_exc] + [f"missing artifact: {m}" for m in missing]
        if missing or any(v in ("fail", "missing") for _, v in tests):
            result = "FAIL"
        elif not tests or any(v == "skip" for _, v in tests):
            result = "BLOCKED"
            blockers.append("no passing automated test bound" if not tests else "a bound test was skipped")
        else:
            result = "IMPLEMENTED_LOCALLY_VERIFIED"
        comps.append({"schema": "INV67_EVIDENCE/1", "item": n, "title": c["title"], "priority": c["priority"],
                      "audit_mapping": c["audit_mapping"], "requirements": rids, "artifacts": arts,
                      "tests": [{"id": i, "result": v} for i, v in tests], "result": result,
                      "acceptance_gate": "MET" if result == "IMPLEMENTED_LOCALLY_VERIFIED" and not open_exc else "NOT_MET",
                      "blockers": blockers, "owner": owner, "environment": env})
    return {"components": comps, "traceability": trace}


def chain(entries: list[dict], key: bytes | None) -> dict:
    prev, out = "0" * 64, []
    for e in entries:
        d = hashlib.sha256((prev + json.dumps(e, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()
        out.append({"item": e["item"], "digest": d, "prev": prev})
        prev = d
    seal = ({"alg": "HMAC-SHA256", "mac": hmac.new(key, prev.encode(), hashlib.sha256).hexdigest()} if key
            else {"alg": "unsigned", "note": "tamper-evident hash chain only; no protected signing key (EXC-004)"})
    return {"schema": "INV67_ACCEPTANCE_BUNDLE/1", "head": prev, "links": out, "seal": seal}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    t0 = time.time()
    outcomes = run_tests()
    ev = evaluate(outcomes)
    comps = ev["components"]
    counts = {k: sum(1 for c in comps if c["result"] == k) for k in ("IMPLEMENTED_LOCALLY_VERIFIED", "BLOCKED", "FAIL")}
    met = sum(1 for c in comps if c["acceptance_gate"] == "MET")
    tsum = {k: sum(1 for v in outcomes.values() if v == k) for k in ("pass", "fail", "skip")}
    roles_null = [k for k, v in json.loads((ROOT / "docs/governance/ownership.json").read_text())["roles"].items() if v is None]
    verdict = "GO" if met == 68 and not roles_null and tsum["fail"] == 0 else "NO_GO"
    result = {"schema": "INV67_GATE_RESULT/1", "version": (ROOT / "VERSION").read_text().strip(), "verdict": verdict,
              "components": counts, "acceptance_gates_met": met, "acceptance_gates_total": 68, "tests": tsum,
              "unassigned_roles": roles_null, "seconds": round(time.time() - t0, 2),
              "blocking_exceptions": sorted({b.split(":")[0] for c in comps for b in c["blockers"] if b.startswith("EXC-")}),
              "failed_tests": sorted(k for k, v in outcomes.items() if v == "fail")}
    if not a.no_write:
        (EV / "components").mkdir(parents=True, exist_ok=True)
        for c in comps:
            (EV / "components" / f"{c['item']:02d}.json").write_text(json.dumps(c, indent=1, sort_keys=True) + "\n")
        (EV / "test_results.json").write_text(json.dumps(dict(sorted(outcomes.items())), indent=1) + "\n")
        (EV / "TRACEABILITY.json").write_text(json.dumps(ev["traceability"], indent=1) + "\n")
        key = os.environ.get("INV67_EVIDENCE_KEY", "").encode() or None
        (EV / "ACCEPTANCE_BUNDLE.json").write_text(json.dumps(chain(comps, key), indent=1) + "\n")
        (EV / "GATE_RESULT.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    if result["failed_tests"] or counts["FAIL"]:
        return 2
    return 1 if (a.release and verdict != "GO") else 0


if __name__ == "__main__":
    sys.exit(main())
