"""MC-19: run the suites + benchmark and emit machine-verifiable gate evidence.

Writes evidence/pk_evidence.jsonl (one record per test and per benchmark) and
conformance/PK_GATE_RESULTS.json (gate verdicts). If INV10_SIGNING_KEY is set, the
gate record is HMAC-signed. Verdicts are computed, never asserted: a failing test or
an unmet SLO yields NO_GO. pk_core-bound checks are reported SKIPPED, not passed.
"""
import datetime, hashlib, hmac, json, os, subprocess, sys, unittest
import _path  # noqa: F401
from _path import ROOT
import bench
from inv10_component_composition_system import __version__

TESTS = ROOT / "inv10_component_composition_system" / "tests"


class Rec(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []
    def addSuccess(self, t):
        super().addSuccess(t); self.rows.append((t.id(), "pass", ""))
    def addFailure(self, t, e):
        super().addFailure(t, e); self.rows.append((t.id(), "fail", self._exc_info_to_string(e, t)[-400:]))
    def addError(self, t, e):
        super().addError(t, e); self.rows.append((t.id(), "error", self._exc_info_to_string(e, t)[-400:]))
    def addSkip(self, t, r):
        super().addSkip(t, r); self.rows.append((t.id(), "skip", r))


def run_suite(optimize=False):
    if optimize:  # re-run under python -O in a subprocess
        r = subprocess.run([sys.executable, "-O", "-m", "unittest", "discover", "-s", str(TESTS), "-t", str(TESTS)],
                           capture_output=True, text=True, cwd=TESTS)
        return r.returncode == 0, r.stderr.strip().splitlines()[-1] if r.stderr else ""
    sys.path.insert(0, str(TESTS))
    suite = unittest.defaultTestLoader.discover(str(TESTS), top_level_dir=str(TESTS))
    res = unittest.TextTestRunner(resultclass=Rec, verbosity=0, stream=open(os.devnull, "w")).run(suite)
    return res


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    res = run_suite()
    ok_o, tail_o = run_suite(optimize=True)
    b = bench.run(200, 500, 7)
    (ROOT / "evidence").mkdir(exist_ok=True)
    rows = [{"kind": "test", "id": i, "outcome": o, "detail": d, "at": now, "version": __version__} for i, o, d in res.rows]
    rows.append({"kind": "test-optimized", "outcome": "pass" if ok_o else "fail", "detail": tail_o, "at": now})
    rows.append({"kind": "benchmark", "at": now, **b})
    (ROOT / "evidence" / "pk_evidence.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    counts = {k: sum(1 for r in res.rows if r[1] == k) for k in ("pass", "fail", "error", "skip")}
    gates = {
        "unit_integration_property": "GO" if counts["fail"] == counts["error"] == 0 else "NO_GO",
        "optimized_mode": "GO" if ok_o else "NO_GO",
        "latency_slo_p99_200ms_at_200": "GO" if b["slo_met"] else "NO_GO",
        "conformance_vectors": "GO" if all(r[1] == "pass" for r in res.rows if "TestConformanceVectors" in r[0]) and any("TestConformanceVectors" in r[0] for r in res.rows) else "NO_GO",
        "pk_core_framework_conformance": "BLOCKED" if counts["skip"] else "GO",
        "adjacent_services_real_integration": "BLOCKED",
        "ownership_and_adr_signed": "BLOCKED",
    }
    overall = "NO_GO" if "NO_GO" in gates.values() else ("CONDITIONAL_GO" if "BLOCKED" in gates.values() else "GO")
    ev_digest = hashlib.sha256((ROOT / "evidence" / "pk_evidence.jsonl").read_bytes()).hexdigest()
    gate = {"component": "INV-10", "version": __version__, "generated_at": now, "tests": counts,
            "benchmark": {k: b[k] for k in ("p50_ms", "p95_ms", "p99_ms", "max_ms", "host")},
            "gates": gates, "overall": overall, "evidence_sha256": ev_digest,
            "blocked_reasons": {
                "pk_core_framework_conformance": "pk_core not bundled; tests/test_component.py skips",
                "adjacent_services_real_integration": "INV-09/11/12/PLN-02 exercised via reference ports only",
                "ownership_and_adr_signed": "docs/OWNERSHIP.md unsigned; ADR-0001 Proposed"}}
    k = os.environ.get("INV10_SIGNING_KEY", "").encode()
    if len(k) >= 16:
        body = json.dumps(gate, sort_keys=True).encode()
        gate["signature"] = {"alg": "HMAC-SHA256", "key_id": hashlib.sha256(k).hexdigest()[:16],
                             "value": hmac.new(k, body, "sha256").hexdigest()}
    (ROOT / "conformance" / "PK_GATE_RESULTS.json").write_text(json.dumps(gate, indent=1) + "\n")
    print(json.dumps({"overall": overall, "tests": counts, "gates": gates}, indent=1))
    return 0 if overall != "NO_GO" else 1


if __name__ == "__main__":
    sys.exit(main())
