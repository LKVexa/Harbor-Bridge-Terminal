"""Generate machine-readable release evidence (components 11, 35, 38, 89, 99).

Runs the full test suite in-process, maps each test to its checklist component by the
``test_cNN`` naming rule, runs adapter conformance, provider certification (SKIPPED
without provisioned providers), captures the benchmark, and writes:

  evidence/test_results.json        every test id -> PASS/FAIL/ERROR/SKIP
  evidence/conformance.json         shared conformance suite per adapter
  evidence/component_status.json    100 components: status, tests, artifacts, gaps, gate
  evidence/traceability.json        REQ id -> implementation -> tests -> evidence -> gate
  evidence/sbom.cdx.json            CycloneDX 1.5 SBOM (runtime deps: none; extras listed)
  evidence/checksums.sha256         sha256 of every shipped file
  evidence/exit_gate.json           C100 production exit gate record
  evidence/evidence_chain.json      sha256 chain over the evidence files above

Gate rules (never relaxed): a component is PASS only if its status is LOCAL_VERIFIED, all of
its mapped tests pass, AND an independent review record exists.  No review record exists in
this pass, so no component can be PASS; the verdict is computed, not asserted.
"""
from __future__ import annotations

import glob
import hashlib
import io
import json
import pathlib
import re
import sys
import time
import unittest

sys.dont_write_bytecode = True
PKG = pathlib.Path(__file__).resolve().parents[1]
EV = PKG / "evidence"
sys.path.insert(0, str(PKG.parent))
sys.path.insert(0, str(PKG / "tests"))
from importlib import import_module  # noqa: E402

pkg = import_module(PKG.name)
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class _Collect(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.outcomes: dict[str, str] = {}

    def addSuccess(self, t):
        super().addSuccess(t)
        self.outcomes.setdefault(t.id(), "PASS")

    def addFailure(self, t, e):
        super().addFailure(t, e)
        self.outcomes[t.id()] = "FAIL"

    def addError(self, t, e):
        super().addError(t, e)
        self.outcomes[t.id()] = "ERROR"

    def addSkip(self, t, r):
        super().addSkip(t, r)
        self.outcomes[t.id()] = f"SKIP: {r}"

    def addSubTest(self, test, sub, err):
        super().addSubTest(test, sub, err)
        if err is not None:
            self.outcomes[test.id()] = "FAIL"


def run_tests() -> dict[str, str]:
    suite = unittest.defaultTestLoader.discover(str(PKG / "tests"), pattern="test_*.py", top_level_dir=str(PKG / "tests"))
    runner = unittest.TextTestRunner(stream=io.StringIO(), resultclass=_Collect, verbosity=0)
    res = runner.run(suite)
    return dict(sorted(res.outcomes.items()))


def conformance() -> dict:
    ad = import_module(f"{PKG.name}.adapters")
    k = import_module(f"{PKG.name}.adapters.kafka")
    r = import_module(f"{PKG.name}.adapters.rabbitmq")
    s = import_module(f"{PKG.name}.adapters.sqs")
    fakes = import_module("fakes")
    _, pf, cf = fakes.kafka_factories()
    sq = fakes.FakeSQS()
    ch = fakes.FakeChannel()
    return {
        "reference-log": {"client": "in-process", "checks": ad.run_conformance(ad.ReferenceLogAdapter())},
        "reference-queue": {"client": "in-process", "checks": ad.run_conformance(ad.ReferenceQueueAdapter())},
        "kafka": {"client": "FAKE (tests/fakes.py) — not evidence about a real cluster",
                  "checks": ad.run_conformance(k.KafkaAdapter(k.build_config(["fake:9092"]), producer_factory=pf,
                                                              consumer_factory=cf))},
        "rabbitmq": {"client": "FAKE (tests/fakes.py) — not evidence about a real broker",
                     "checks": ad.run_conformance(r.RabbitMQAdapter(channel_factory=lambda: ch))},
        "sqs": {"client": "FAKE (tests/fakes.py) — not evidence about AWS",
                "checks": ad.run_conformance(s.SQSAdapter(client=sq),
                                             advance=lambda: setattr(sq, "now", sq.now + 31))},
    }


GENERATED = {"evidence/test_results.json", "evidence/conformance.json", "evidence/component_status.json",
             "evidence/traceability.json", "evidence/sbom.cdx.json", "evidence/checksums.sha256",
             "evidence/exit_gate.json", "evidence/evidence_chain.json", "evidence/"}


def artifact_exists(a: str) -> bool:
    """A claimed artifact must exist: a path, a glob, a generated output, or module.symbol."""
    path = a.split("::")[0].split(" ")[0]
    if path in GENERATED or (PKG / path).exists() or glob.glob(str(PKG / path)):
        return True
    if "." in path and "/" not in path:
        mod, sym = path.split(".", 1)
        f = PKG / f"{mod}.py"
        return f.exists() and re.search(rf"^\s*{re.escape(sym)}\b", f.read_text(), re.M) is not None
    return False


def compute_gate(comps: list[dict], summary: dict) -> tuple[str, list[str], list[str]]:
    """PASS needs LOCAL_VERIFIED + passing tests + independent review; verdict follows P0."""
    for c in comps:
        c["gate"] = "FAIL" if c["status"] == "FAIL" else (
            "PASS" if c["status"] == "LOCAL_VERIFIED" and c.get("independent_review") else "UNVERIFIED")
    p0 = [c["id"] for c in comps if c["priority"] == "P0" and c["gate"] != "PASS"]
    p1 = [c["id"] for c in comps if c["priority"] == "P1" and c["gate"] != "PASS"]
    if p0 or summary.get("FAIL") or summary.get("ERROR"):
        return "NO_GO", p0, p1
    return ("CONDITIONAL_GO" if p1 else "GO"), p0, p1


def shipped_files() -> list[pathlib.Path]:
    return sorted(p for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and "evidence" not in p.relative_to(PKG).parts and ".venv" not in p.parts)


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    EV.mkdir(exist_ok=True)
    tests = run_tests()
    (EV / "test_results.json").write_text(json.dumps(
        {"schema": "inv54.test_results/1", "ts": NOW, "python": sys.version.split()[0],
         "summary": {k: sum(1 for v in tests.values() if v.split(":")[0] == k) for k in ("PASS", "FAIL", "ERROR", "SKIP")},
         "tests": tests}, indent=1))

    conf = conformance()
    (EV / "conformance.json").write_text(json.dumps({"schema": "inv54.conformance/1", "ts": NOW, "adapters": conf},
                                                    indent=1))
    cert_path = EV / "provider_certification.json"
    if not cert_path.exists():
        import subprocess
        subprocess.run([sys.executable, "-B", str(PKG / "tools" / "certify_providers.py")], capture_output=True)
    cert = json.loads(cert_path.read_text())
    bench = json.loads((EV / "benchmark.json").read_text()) if (EV / "benchmark.json").exists() else None

    reg = json.loads((PKG / "tools" / "component_registry.json").read_text())["components"]
    comps = []
    for c in reg:
        mine = {t: v for t, v in tests.items() if re.search(rf"\.{c['test_prefix']}(_|$)", t)}
        # tests covering several components are named test_cAA_cBB_*
        mine.update({t: v for t, v in tests.items() if re.search(rf"_c{c['id']}_", t) and t not in mine})
        failed = [t for t, v in mine.items() if v in ("FAIL", "ERROR")]
        missing = [a for a in c["artifacts"] if not artifact_exists(a)]
        status = c["status"]
        notes = []
        if failed:
            status, notes = "FAIL", notes + [f"failing tests: {failed}"]
        if status == "LOCAL_VERIFIED" and not any(v == "PASS" for v in mine.values()):
            status, notes = "PARTIAL", notes + ["no passing mapped test; downgraded"]
        if missing:
            status, notes = ("FAIL" if status == "LOCAL_VERIFIED" else status), notes + [f"missing artifacts: {missing}"]
        gate_reason = [] if status == "LOCAL_VERIFIED" else [f"status {status}"]
        gate_reason.append("no independent review record (the builder may not review its own work)")
        if c["gaps"]:
            gate_reason.append(c["gaps"])
        comps.append({**{k: c[k] for k in ("id", "priority", "title", "controls", "artifacts", "gaps")},
                      "status": status, "tests": mine, "notes": notes,
                      "independent_review": None, "gate_reasons": gate_reason})
    summary = {k: sum(1 for v in tests.values() if v.split(":")[0] == k) for k in ("PASS", "FAIL", "ERROR", "SKIP")}
    verdict, p0_open, p1_open = compute_gate(comps, summary)
    counts: dict[str, int] = {}
    for c in comps:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    (EV / "component_status.json").write_text(json.dumps(
        {"schema": "inv54.component_status/1", "ts": NOW, "version": pkg.__version__,
         "status_legend": {
             "LOCAL_VERIFIED": "implemented; mapped automated tests pass in the build environment",
             "PARTIAL": "implemented in part; named gaps remain",
             "DOCUMENTED_UNAPPROVED": "normative artifact exists; no approval record",
             "UNVERIFIED_EXTERNAL": "requires an external resource/decision not available to this pass",
             "FAIL": "a mapped test failed or a claimed artifact is missing"},
         "counts": counts, "components": comps}, indent=1))

    # traceability (component 11)
    req_text = (PKG / "docs" / "REQUIREMENTS.md").read_text()
    trace = []
    for line in req_text.splitlines():
        m = re.match(r"^(?:- \*\*|\| )(REQ-[A-Z]+-[A-Z0-9-]+|NFR-[A-Z]+-\d+)", line)
        if not m:
            continue
        rid = m[1]
        tnames = re.findall(r"`(test_c\d\d[a-z0-9_]*)\*?`", line)
        matched = {t: v for t, v in tests.items() for tn in tnames if tn.rstrip("_") in t}
        impl = re.findall(r"`([a-z_]+\.[A-Za-z_]+|[a-z_]+\.py)`", line)
        trace.append({"requirement": rid, "source": "docs/REQUIREMENTS.md", "implementation": impl,
                      "tests": matched, "runtime_evidence": "evidence/test_results.json",
                      "gate": "UNVERIFIED" if matched and all(v == "PASS" for v in matched.values())
                      else "NO_EVIDENCE" if not matched else "FAIL"})
    for c in comps:
        trace.append({"requirement": f"INV54-COMP-{c['id']}", "controls": c["controls"],
                      "source": "docs/checklist/INV54_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md",
                      "implementation": c["artifacts"], "tests": c["tests"],
                      "runtime_evidence": "evidence/component_status.json", "gate": c["gate"]})
    orphans = [t["requirement"] for t in trace if t["gate"] == "NO_EVIDENCE"]
    (EV / "traceability.json").write_text(json.dumps({"schema": "inv54.traceability/1", "ts": NOW,
                                                      "orphans_without_test": orphans, "rows": trace}, indent=1))

    # SBOM + checksums (components 35, 38)
    py = __import__("tomllib").loads((PKG / "pyproject.toml").read_text())
    sbom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": NOW, "component": {"type": "library", "name": py["project"]["name"],
                                                         "version": pkg.__version__}},
            "components": [{"type": "library", "name": r.split("==")[0], "version": r.split("==")[1],
                            "scope": "optional", "properties": [{"name": "inv54:extra", "value": extra}]}
                           for extra, reqs in py["project"]["optional-dependencies"].items() for r in reqs],
            "dependencies": [{"ref": py["project"]["name"], "dependsOn": []}]}
    (EV / "sbom.cdx.json").write_text(json.dumps(sbom, indent=1))
    files = shipped_files()
    (EV / "checksums.sha256").write_text("".join(f"{sha(p)}  {p.relative_to(PKG).as_posix()}\n" for p in files))

    # exit gate (component 99)
    gate = {"schema": "inv54.exit_gate/1", "ts": NOW, "element": "INV-54", "version": pkg.__version__,
            "verdict": verdict,
            "tests": summary, "component_counts": counts,
            "p0_not_pass": p0_open, "p1_not_pass": p1_open,
            "provider_certification": {k: v["status"] for k, v in cert["providers"].items()},
            "pk_core_certification": "SKIPPED (pk_core not supplied)",
            "benchmark_env": bench["environment"] if bench else None,
            "waivers_approved": [], "signed_by": None,
            "statement": "No component is PASS: every one lacks an independent review record, and provider, "
                         "pk_core, edge and fleet evidence is absent. Local verification results are in "
                         "component_status.json."}
    (EV / "exit_gate.json").write_text(json.dumps(gate, indent=1))

    chain, prev = [], "0" * 64
    for name in ("test_results.json", "conformance.json", "provider_certification.json", "benchmark.json",
                 "component_status.json", "traceability.json", "sbom.cdx.json", "checksums.sha256", "exit_gate.json"):
        p = EV / name
        if p.exists():
            d = sha(p)
            prev = hashlib.sha256((prev + d).encode()).hexdigest()
            chain.append({"file": name, "sha256": d, "chain": prev})
    (EV / "evidence_chain.json").write_text(json.dumps({"schema": "inv54.evidence_chain/1", "ts": NOW,
                                                        "head": prev, "links": chain}, indent=1))
    print(json.dumps({"tests": summary, "components": counts, "verdict": gate["verdict"],
                      "orphans": len(orphans), "head": prev[:16]}, indent=1))
    return 0 if not (summary["FAIL"] or summary["ERROR"]) else 1


if __name__ == "__main__":
    sys.exit(main())
