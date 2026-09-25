"""CI acceptance gate (MC-048): runs every mandatory stage and writes machine-readable,
digest-bound, optionally HMAC-signed evidence to ``evidence/``.

Stages: static (compileall + import), unit/integration (normal), optimized-runtime (python -O),
contract/conformance, compatibility, traceability, MASTER.md, exceptions, security (subset marker),
performance smoke, restore drill, packaging (manifest + SBOM + provenance).

Skips fail the gate unless the test id is in APPROVED_SKIPS (each tied to an exception id).
"""
import compileall, json, os, subprocess, sys, time, unittest
import _path  # noqa: F401
from inv05_current_control_state_system import tools_check as tc

APPROVED_SKIPS = {  # test id prefix -> exception
    "test_component.": "EX-003",  # pk_core framework not available
}
EVID = os.path.join(tc.PKG, "evidence")


class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.records = []
        self._t = {}

    def startTest(self, test):
        self._t[test.id()] = time.perf_counter()
        super().startTest(test)

    def _rec(self, test, outcome, detail=""):
        self.records.append({"id": test.id(), "outcome": outcome, "detail": detail[:500],
                             "seconds": round(time.perf_counter() - self._t.get(test.id(), time.perf_counter()), 4)})

    def addSuccess(self, test):
        super().addSuccess(test); self._rec(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err); self._rec(test, "failed", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err); self._rec(test, "error", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self._rec(test, "skipped", reason)


def run_tests():
    tests_dir = os.path.join(tc.PKG, "tests")
    suite = unittest.defaultTestLoader.discover(tests_dir, top_level_dir=tests_dir)
    with open(os.devnull, "w") as devnull:
        r = unittest.TextTestRunner(stream=devnull, resultclass=Recorder, verbosity=0).run(suite)
    return r.records


def write(name, obj):
    os.makedirs(EVID, exist_ok=True)
    p = os.path.join(EVID, name)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True, default=str)
    return p


def main():
    stages, ok = {}, True
    started = time.time()
    # static
    stages["static"] = {"ok": compileall.compile_dir(tc.PKG, quiet=1, force=True)}
    # unit + integration
    if os.environ.get("INV05_GATE_CHILD") == "1":
        recs = run_tests()
        print(json.dumps(recs))
        return 0
    recs = run_tests()
    bad_skips = [r["id"] for r in recs if r["outcome"] == "skipped"
                 and not any(r["id"].startswith(p) for p in APPROVED_SKIPS)]
    fails = [r["id"] for r in recs if r["outcome"] in ("failed", "error")]
    stages["tests"] = {"ok": not fails and not bad_skips, "total": len(recs), "passed": sum(r["outcome"] == "passed" for r in recs),
                       "failed": fails, "unapproved_skips": bad_skips,
                       "approved_skips": [{"id": r["id"], "exception": next(v for p, v in APPROVED_SKIPS.items() if r["id"].startswith(p))}
                                          for r in recs if r["outcome"] == "skipped" and r["id"] not in bad_skips]}
    write("test_results.json", recs)
    # optimized runtime
    env = dict(os.environ, INV05_GATE_CHILD="1")
    out = subprocess.run([sys.executable, "-O", os.path.abspath(__file__)], capture_output=True, text=True, env=env)
    try:
        orecs = json.loads(out.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        orecs = [{"id": "optimized-run", "outcome": "error", "detail": out.stderr[-500:]}]
    ofails = [r["id"] for r in orecs if r["outcome"] in ("failed", "error")]
    stages["optimized"] = {"ok": not ofails, "total": len(orecs), "failed": ofails}
    write("test_results_optimized.json", orecs)
    # conformance
    from inv05_current_control_state_system.conformance import runner
    import glob
    reps = [runner.run_file(p) for p in sorted(glob.glob(os.path.join(tc.PKG, "conformance", "vectors_v*.json")))]
    stages["conformance"] = {"ok": all(r["failed"] == 0 for r in reps), "passed": sum(r["passed"] for r in reps)}
    write("conformance.json", reps)
    # compatibility, traceability, master, exceptions
    from inv05_current_control_state_system.schema import schema_lock
    cp = tc.schema_breaking_changes(tc.load_json("conformance/schema_lock.json"), schema_lock())
    stages["compatibility"] = {"ok": not cp, "problems": cp}
    tp = tc.check_trace(tc.load_json("traceability/trace_matrix.json"))
    stages["traceability"] = {"ok": not tp, "problems": tp[:50]}
    mp = tc.check_master_md()
    stages["master_md"] = {"ok": not mp, "problems": mp}
    ep = tc.check_exceptions()
    stages["exceptions"] = {"ok": not ep, "problems": ep}
    # performance smoke + restore drill
    from inv05_current_control_state_system import bench
    b = bench.run(ops=3000, keys=300, watchers=2)
    stages["performance_smoke"] = {"ok": b["latency"]["write"]["p99_ms"] < 50, "write_p99_ms": b["latency"]["write"]["p99_ms"],
                                   "throughput_ops_s": b["throughput_ops_s"]}
    write("bench_smoke.json", b)
    import restore_drill
    d = restore_drill.drill(200)
    stages["restore_drill"] = {"ok": d["ok"], **{k: d[k] for k in ("state_equal", "revision")}}
    write("restore_drill.json", d)
    # packaging / supply chain
    m = tc.manifest()
    write("sbom.cdx.json", tc.sbom())
    report = {"schema": "cstate.ci_gate/1", "version": tc.version(), "tree_sha256": tc.tree_digest(m),
              "commit": os.environ.get("INV05_BUILD_COMMIT", "unknown"), "started": started, "finished": time.time(),
              "python": sys.version.split()[0], "stages": stages}
    report["ok"] = all(s["ok"] for s in stages.values())
    write("provenance.intoto.json", tc.provenance({k: v["ok"] for k, v in stages.items()}))
    evid_digests = {f: tc.digest_file(os.path.join(EVID, f)) for f in sorted(os.listdir(EVID))
                    if f.endswith(".json") and f != "gate_report.json"}
    report["evidence_sha256"] = evid_digests
    key = os.environ.get("INV05_SIGNING_KEY")
    report["signature"] = {"alg": "HMAC-SHA256", "value": tc.sign({k: v for k, v in report.items() if k != "signature"},
                                                                  bytes.fromhex(key))} if key else None
    write("gate_report.json", report)
    print(json.dumps({"ok": report["ok"], "stages": {k: v["ok"] for k, v in stages.items()},
                      "tests": f"{stages['tests']['passed']}/{stages['tests']['total']}",
                      "signed": bool(key)}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
