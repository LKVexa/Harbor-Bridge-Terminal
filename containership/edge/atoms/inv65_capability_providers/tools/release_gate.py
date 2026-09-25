"""INV-65 release gate (M29/M30): runs every executable check, writes
machine-readable evidence, and records the formal gate verdict.

    python -m inv65_capability_providers.tools.release_gate [--quick]

Verdict rules (never optimistic):
  NO_GO           any executed check fails, or any P0 missing component is blocked
  CONDITIONAL_GO  all executed checks pass and only P1/P2 conditions remain
  GO              everything passed, nothing blocked, independent review recorded
A skipped / not-run check is recorded as not_run, never as pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time

if __package__ in (None, ""):
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
    __package__ = "inv65_capability_providers.tools"

from ..supply_chain.trust import provenance, sbom  # noqa: E402
from .verify_evidence import GENESIS, rec_digest  # noqa: E402

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
PY = sys.executable
P0_BLOCKED_REASON = {
    "M02": "pk_core unresolvable: no source/version/digest supplied",
    "M23": "real INV-60/55/64/61 layers absent; only contract stubs tested",
}
P1P2_CONDITIONS = {
    "M01": "MASTER.md corpus absent (not fabricated)",
    "M37": "licence not chosen by owner",
    "M22": "dashboards/alerts not loaded into a live monitoring stack",
    "M27": "fleet-scale/soak-at-scale not run",
    "M28": "only CPython 3.11 x86_64 linux tested",
    "M32": "owner/reviewer UNASSIGNED; ADR-0001 PROPOSED",
    "M34": "review calendar never held",
    "M39": "SLOs measured on one host only",
}


def sh(args, timeout=900):
    t0 = time.time()
    p = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout,
                       env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin:/usr/local/bin"})
    return p.returncode, (p.stdout + p.stderr)[-4000:], round(time.time() - t0, 2)


def write(rel, text):
    p = PKG / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="shorter fuzz/soak")
    ap.add_argument("--print-digest", action="store_true")
    a = ap.parse_args(argv)
    version = (PKG / "VERSION").read_text().strip()
    s = sbom(version)
    impl_digest = hashlib.sha256(json.dumps([(c["name"], c["hashes"][0]["content"]) for c in s["components"]
                                             if not c["name"].startswith(("conformance/PK_GATE", "supply_chain/provider_catalog", "traceability/"))],
                                            sort_keys=True).encode()).hexdigest()
    if a.print_digest:
        print(impl_digest); return 0
    mod = PKG.name
    for stale in ("evidence/pk_evidence.jsonl", "conformance/PK_GATE_RESULTS.json"):
        (PKG / stale).unlink(missing_ok=True)  # never let a previous run's chain be verified against new artifacts
    checks = []

    def run(check, args, artifact, parse=None):
        rc, out, dur = sh(args)
        status = "pass" if rc == 0 else "fail"
        extra = parse(out) if parse else {}
        write(artifact, json.dumps({"check": check, "argv": args[1:], "exit": rc, "duration_s": dur, "tail": out[-2500:], **extra}, indent=1) + "\n")
        checks.append({"check": check, "status": status, "artifact": artifact})

    def unit_counts(out):
        import re
        m = re.search(r"Ran (\d+) tests", out); sk = re.search(r"skipped=(\d+)", out)
        return {"ran": int(m.group(1)) if m else 0, "skipped": int(sk.group(1)) if sk else 0}

    run("compile", [PY, "-m", "compileall", "-q", mod], "evidence/compile-results.json")
    run("tests", [PY, "-B", "-W", "ignore", "-m", "unittest", "discover", "-s", f"{mod}/tests", "-t", "."], "evidence/test-results.json", unit_counts)
    run("tests_optimized", [PY, "-O", "-B", "-W", "ignore", "-m", "unittest", "discover", "-s", f"{mod}/tests", "-t", "."], "evidence/test-results-O.json", unit_counts)
    run("rtm", [PY, "-B", f"{mod}/tools/check_rtm.py"], "evidence/rtm-results.json")
    run("fuzz", [PY, "-B", "-m", f"{mod}.fuzz.harness", "--iterations", "3000" if a.quick else "30000", "--seed", "65",
                 "--out", f"{mod}/evidence/fuzz-results.json"], "evidence/fuzz-run.json")
    run("performance", [PY, "-B", "-m", f"{mod}.benchmarks.harness", "--soak-s", "2" if a.quick else "10",
                        "--out", f"{mod}/evidence/performance-results.json"], "evidence/performance-run.json")
    run("pk_core", [PY, "-B", f"{mod}/ci/scripts/check_pk_core.py"], "evidence/pk_core-check.json")
    # conformance (pk_core) -- honest not_run when unavailable
    rc, out, _ = sh([PY, "-c", "import pk_core"])
    checks.append({"check": "conformance_100", "status": "pass" if rc == 0 else "not_run",
                   "artifact": "evidence/pk_core-check.json", "note": "pk_core not importable" if rc else ""})
    # fault evidence = the fault tests' own matrix + test results
    write("evidence/fault-results.json", json.dumps({"matrix": json.loads((PKG / "tests/fault/fault_matrix.json").read_text()),
                                                      "executed_by": "evidence/test-results.json"}, indent=1) + "\n")
    checks.append({"check": "fault_matrix", "status": checks[1]["status"], "artifact": "evidence/fault-results.json"})
    import platform
    write("evidence/compatibility-results.json", json.dumps({"python": platform.python_version(), "machine": platform.machine(),
                                                             "system": platform.system(), "tests": checks[1]["status"]}, indent=1) + "\n")
    checks.append({"check": "compatibility_local", "status": checks[1]["status"], "artifact": "evidence/compatibility-results.json"})
    # SLO evidence from measured results
    from ..slo.error_budget import evaluate
    perf = json.loads((PKG / "evidence/performance-results.json").read_text())
    fuzz = json.loads((PKG / "evidence/fuzz-results.json").read_text())
    tests_ok = checks[1]["status"] == "pass"
    meas = {"isolation": {"bad": 0 if tests_ok else 1, "total": 1},
            "restart_continuity": {"bad": 0 if tests_ok else 1, "total": 1},
            "revocation_durability": {"bad": 0 if tests_ok else 1, "total": 1},
            "call_overhead": {"bad": perf["dispatch"]["over_1ms"], "total": perf["dispatch"]["n"]}}
    slo = evaluate(meas)
    slo["note"] = "isolation/restart/revocation SLIs are test-suite pass/fail proxies on one host, not production telemetry"
    write("evidence/slo-results.json", json.dumps(slo, indent=1) + "\n")
    checks.append({"check": "slo", "status": "pass" if slo["verdict"] == "PASS" else "fail", "artifact": "evidence/slo-results.json"})
    # SBOM / provenance / catalog pin
    write("sbom/inv65-4.3.0.cdx.json", json.dumps(s, indent=1) + "\n")
    prov = provenance(version, s)
    write("provenance/inv65-4.3.0.intoto.json", json.dumps(prov, indent=1) + "\n")
    cat = json.loads((PKG / "supply_chain/provider_catalog.json").read_text())
    cat["contracts"]["wasi:keyvalue"][0]["sha256"] = impl_digest
    write("supply_chain/provider_catalog.json", json.dumps(cat, indent=1) + "\n")
    # evidence chain
    prev, lines = GENESIS, []
    for c in checks:
        art = PKG / c["artifact"]
        r = {"schema": "PK_EVIDENCE/1", "element": "INV-65", "version": version, "check": c["check"], "status": c["status"],
             "artifact": c["artifact"], "artifact_digest": hashlib.sha256(art.read_bytes()).hexdigest(), "note": c.get("note", ""), "prev": prev}
        r["digest"] = rec_digest(r); prev = r["digest"]; lines.append(json.dumps(r, sort_keys=True))
    write("evidence/pk_evidence.jsonl", "\n".join(lines) + "\n")
    failed = [c["check"] for c in checks if c["status"] == "fail"]
    not_run = [c["check"] for c in checks if c["status"] == "not_run"]
    verdict = "NO_GO" if failed or P0_BLOCKED_REASON else ("CONDITIONAL_GO" if P1P2_CONDITIONS or not_run else "GO")
    gate = {"schema": "PK_GATE_RESULTS/1", "element": "INV-65", "version": version, "verdict": verdict,
            "evidence_head": prev, "implementation_digest": impl_digest, "checks": checks, "failed": failed, "not_run": not_run,
            "p0_blockers": P0_BLOCKED_REASON, "conditions": P1P2_CONDITIONS, "fuzz_crashes": len(fuzz["crashes"]),
            "independent_review": None, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "rule": "NO_GO while any executed check fails or any P0 component is blocked; skipped != pass"}
    write("conformance/PK_GATE_RESULTS.json", json.dumps(gate, indent=1) + "\n")
    manifest = {"element": "INV-65", "version": version, "files": {c["name"]: c["hashes"][0]["content"] for c in s["components"]},
                "sbom_sha256": hashlib.sha256((PKG / "sbom/inv65-4.3.0.cdx.json").read_bytes()).hexdigest(),
                "provenance_sha256": hashlib.sha256((PKG / "provenance/inv65-4.3.0.intoto.json").read_bytes()).hexdigest(),
                "evidence_head": prev, "gate_verdict": verdict, "signed": False}
    write("release/manifest.json", json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"verdict": verdict, "failed": failed, "not_run": not_run, "evidence_head": prev[:16]}))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
