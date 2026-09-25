"""INV-23 production gate (MC-14).  Runs every mandatory job, the pk_core W0-W9 workflow,
the SLO benchmark and the host probe, then writes sealed, hash-chained evidence:

  conformance/PK_GATE_RESULTS.json      gate result (schemas/PK_GATE_RESULTS-1.schema.json)
  conformance/pk_core_gate.json         pk_core's own gate verdict
  evidence/pk_evidence.jsonl            pk_core hash-chained W0-W9 ledger
  evidence/conformance-findings.json    all 100 findings with evidence refs
  evidence/jobs.json                    mandatory job results (incl. python -O)
  evidence/benchmark-results.json       SLO benchmark
  evidence/compatibility-results.json   matrix rows exercised + host probe
  evidence/sbom.cdx.json, evidence/provenance.json
  evidence/inv23_release_ledger.jsonl   release ledger chained to the previous head
  evidence/checksums.sha256             digests of everything above

Usage: python tools/gate.py [--wheel dist/x.whl] [--quick]
Exit: 0 GO, 2 CONDITIONAL_GO, 3 NO_GO, 4 BLOCKED (evidence could not be produced).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sbom as sbom_mod  # noqa: E402
from common import ROOT, canonical, sha256_bytes, sha256_file, source_identity, version  # noqa: E402

EV, CF = ROOT / "evidence", ROOT / "conformance"
MANDATORY = ["unit", "schema", "property", "integration", "multiprocess", "conformance"]
ALLOWED_SKIPS = {
    "tests.unit.test_ownership.PosixDurabilityTest.test_read_only_storage_fails_without_split_brain": (
        "root ignores directory permissions; runs on non-root CI runners"
    ),
}
PKG = ROOT.name


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run(cmd, env=None, timeout=900):
    e = dict(os.environ, **(env or {}))
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=e, timeout=timeout)


def job(suite, optimized=False):
    cmd = [sys.executable] + (["-O"] if optimized else []) + ["tools/run_suite.py", suite]
    p = run(cmd, env={"INV23_CONFORMANCE": "release"})
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {
            "suite": suite,
            "ok": False,
            "ran": 0,
            "failures": [],
            "errors": ["runner crashed"],
            "skipped": [],
            "stderr": p.stderr[-2000:],
            "optimized": optimized,
        }


def pk_workflow():
    sys.path.insert(0, str(ROOT.parent))
    os.environ["INV23_CONFORMANCE"] = "release"
    import importlib

    compat = importlib.import_module(f"{PKG}.pkcore_compat")
    res = compat.resolve()
    if res.status != "ok":
        return res, None, None, None
    from pk_core.evidence import EvidenceLedger
    from pk_core.gate import ConformanceGate
    from pk_core.workflow import WorkflowEngine

    comp = importlib.import_module(PKG).COMPONENT()
    ledger = EvidenceLedger(EV / "pk_evidence.jsonl")
    wf = WorkflowEngine(ledger).run(comp)
    gate = ConformanceGate().evaluate([wf])
    items = {i["check_id"]: i for i in json.loads((ROOT / "CHECKLIST.json").read_text())["items"]}
    findings = []
    for f in wf.findings:
        it = items[f.check_id]
        findings.append(
            {
                "check_id": f.check_id,
                "ordinal": it["ordinal"],
                "dimension": it["dimension"],
                "status": f.status.value,
                "stage": getattr(f.stage, "name", str(f.stage)),
                "note": f.note,
                "statement": f.statement,
                "evidence": list(f.artifacts),
                "waiver": None,
            }
        )
    return res, wf, gate, findings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheel")
    ap.add_argument("--quick", action="store_true", help="smaller benchmark/multiprocess runs (not for release)")
    a = ap.parse_args(argv)
    EV.mkdir(exist_ok=True)
    CF.mkdir(exist_ok=True)
    started = now()
    blockers, conditions = [], []

    # 1. mandatory jobs (normal + optimized)
    env_q = {"INV23_MP_ROUNDS": "5"} if a.quick else {}
    os.environ.update(env_q)
    jobs = {s: job(s) for s in MANDATORY}
    jobs["conformance-O"] = job("conformance", optimized=True)
    jobs["unit-O"] = job("unit", optimized=True)
    for name, j in jobs.items():
        if not j["ok"]:
            blockers.append(f"mandatory job {name} failed: {j['failures'] + j['errors']}")
        for s in j["skipped"]:
            if s["id"] not in ALLOWED_SKIPS:
                blockers.append(f"mandatory job {name} skipped {s['id']}: {s['reason']}")
            else:
                s["allowed"] = ALLOWED_SKIPS[s["id"]]
    static = {}
    for tool, cmd in (
        ("ruff", ["ruff", "check", "."]),
        ("ruff-format", ["ruff", "format", "--check", "."]),
        ("mypy", ["mypy", "--config-file", f"{PKG}/pyproject.toml", "-p", PKG]),
        ("version", [sys.executable, "tools/check_version.py"]),
        ("compat-doc", [sys.executable, "tools/gen_compat.py", "--check"]),
        ("waivers", [sys.executable, "tools/waivers.py"]),
    ):
        if tool in ("ruff", "ruff-format", "mypy") and not shutil.which(cmd[0]):
            static[tool] = {"ok": None, "detail": "tool not installed"}
            blockers.append(f"static gate {tool} not run (tool unavailable)")
            continue
        p = subprocess.run(cmd, cwd=ROOT.parent if tool == "mypy" else ROOT, capture_output=True, text=True)
        static[tool] = {"ok": p.returncode == 0, "detail": (p.stdout + p.stderr)[-1500:]}
        if p.returncode != 0:
            blockers.append(f"static gate {tool} failed")
    (EV / "jobs.json").write_text(json.dumps({"jobs": jobs, "static": static}, indent=1) + "\n")

    # 2. pk_core conformance
    res, wf, pkgate, findings = pk_workflow()
    counts = {"total": 0, "pass": 0, "fail": 0, "blocked": 0, "partial": 0, "waived": 0}
    if res.status != "ok":
        blockers.append(f"pk_core {res.status}: {res.diagnostics} (non-certifiable)")
    else:
        (CF / "pk_core_gate.json").write_text(json.dumps(pkgate.to_dict(), indent=1) + "\n")
        (EV / "conformance-findings.json").write_text(json.dumps(findings, indent=1) + "\n")
        counts["total"] = len(findings)
        for f in findings:
            st = f["status"]
            key = {"satisfied": "pass", "not_applicable": "pass", "partial": "partial", "blocked": "blocked"}.get(st, "fail")
            counts[key] += 1
        if len(findings) != 100 or len({f["check_id"] for f in findings}) != 100:
            blockers.append("pk_core did not answer exactly 100 unique requirements")
        if counts["blocked"]:
            blockers.append(f"{counts['blocked']} blocked requirements")
        if counts["fail"]:
            blockers.append(f"{counts['fail']} failing requirements")
        if pkgate.verdict != "GO":
            blockers.append(f"pk_core gate verdict {pkgate.verdict}: {pkgate.blockers + pkgate.conditions}")

    # 3. SLO
    bench_cmd = [
        sys.executable,
        "benchmarks/benchmark_probe.py",
        "--samples",
        "500" if a.quick else "3000",
        "--out",
        str(EV / "benchmark-results.json"),
    ]
    base = sorted((ROOT / "benchmarks" / "baselines").glob("*.json"))
    if base:
        bench_cmd += ["--baseline", str(base[-1])]
    bp = run(bench_cmd)
    bench = json.loads((EV / "benchmark-results.json").read_text()) if (EV / "benchmark-results.json").exists() else None
    if bench is None or bp.returncode == 1:
        blockers.append("probe p99 SLO failed or benchmark missing")
    elif bp.returncode == 2:
        conditions.append("probe p99 regressed beyond threshold vs baseline")
    elif bp.returncode == 3:
        conditions.append("benchmark environment noisy")
    if bench and bench["environment"]["machine_class"] == "unclassified":
        conditions.append("SLO measured on an unclassified machine, not a qualified benchmark host (WVR-002)")

    # 4. compatibility evidence
    hw = job("hardware")
    compat = json.loads((ROOT / "compatibility.json").read_text())
    verified = [r["id"] for r in compat["rows"] if r["status"] == "verified"]
    from importlib import import_module

    probe_report = import_module(f"{PKG}.probe").probe_host().to_report()
    (EV / "compatibility-results.json").write_text(
        json.dumps(
            {
                "generated_at": now(),
                "host_probe": probe_report,
                "hardware_job": hw,
                "rows_verified": verified,
                "rows_exercised_here": [os.environ.get("INV23_MATRIX_ROW") or "LNX-GUEST-NOVT"],
            },
            indent=1,
        )
        + "\n"
    )
    bm = [r["id"] for r in compat["rows"] if r["status"] == "verified" and r["expected"]["state"] == "usable"]
    if not bm:
        blockers.append("no production platform row (a host where the primitive is usable) has hardware evidence (WVR-001)")

    # 5. governance
    if not (ROOT / "LICENSE").exists():
        blockers.append("no LICENSE: license undetermined (WVR-003)")
    conditions.append("evidence is hash-chained but unsigned (WVR-004)")

    # 6. build artifacts, SBOM, provenance
    artifacts = {}
    if a.wheel:
        artifacts["wheel"] = {"path": pathlib.Path(a.wheel).name, "sha256": sha256_file(a.wheel)}
    else:
        conditions.append("no built wheel supplied to the gate (--wheel)")
    sb = sbom_mod.build(a.wheel)
    (EV / "sbom.cdx.json").write_text(json.dumps(sb, indent=1) + "\n")
    ident = source_identity()
    prov = {
        "_type": "https://in-toto.io/Statement/v1",
        "predicateType": "https://slsa.dev/provenance/v1",
        "subject": [{"name": k, "digest": {"sha256": v["sha256"]}} for k, v in artifacts.items()]
        + [{"name": "source-tree", "digest": {"sha256": ident["tree_sha256"]}}],
        "predicate": {
            "buildDefinition": {
                "buildType": "inv23/tools/gate.py@1",
                "externalParameters": {"quick": a.quick, "wheel": bool(a.wheel)},
                "resolvedDependencies": [
                    {"name": "pk_core", "digest": {"sha256": json.loads((ROOT / "vendor" / "VENDORED.json").read_text())["tree_sha256"]}}
                ],
            },
            "runDetails": {
                "builder": {"id": os.environ.get("GITHUB_WORKFLOW_REF", "local:" + platform.node())},
                "metadata": {"startedOn": started, "finishedOn": now()},
            },
        },
    }
    (EV / "provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    artifacts["sbom"] = {"path": "evidence/sbom.cdx.json", "sha256": sha256_file(EV / "sbom.cdx.json")}
    artifacts["provenance"] = {"path": "evidence/provenance.json", "sha256": sha256_file(EV / "provenance.json")}

    # 7. waivers: only approved & unexpired ones may downgrade a blocker (none are approved today)
    waivers = import_module("waivers").load()
    active = [w["id"] for w in waivers if w["active"]]

    verdict = "NO_GO" if blockers else "CONDITIONAL_GO" if conditions else "GO"
    ledger_path = EV / "inv23_release_ledger.jsonl"
    prev = None
    if ledger_path.exists():
        lines = [ln for ln in ledger_path.read_text().splitlines() if ln.strip()]
        prev = json.loads(lines[-1])["digest"] if lines else None
    gate = {
        "schema": "PK_GATE_RESULTS/1",
        "element": "INV-23",
        "version": version(),
        "verdict": verdict,
        "certifiable": verdict == "GO",
        "generated_at": now(),
        "source": ident,
        "environment": {
            "python": platform.python_version(),
            "os": platform.platform(),
            "arch": platform.machine(),
            "backend": probe_report["backend"],
            "pk_core": res.as_evidence(),
        },
        "counts": counts,
        "checks": [{"check_id": f["check_id"], "status": f["status"]} for f in (findings or [])],
        "mandatory_jobs": {k: {"ok": v["ok"], "ran": v["ran"], "skipped": v["skipped"]} for k, v in jobs.items()},
        "slo": bench
        and {
            "p99_ms": bench["stats"]["p99_ms"],
            "threshold_ms": 50.0,
            "pass": bench["slo"]["pass"],
            "machine_class": bench["environment"]["machine_class"],
        },
        "compatibility": {"rows_verified": verified},
        "static": {k: v["ok"] for k, v in static.items()},
        "artifacts": artifacts,
        "waivers_active": active,
        "blocking_reasons": blockers,
        "conditions": conditions,
        "previous_head": prev,
    }
    sys.path.insert(0, str(ROOT.parent))
    import_module(f"{PKG}.schema").validate(gate, "PK_GATE_RESULTS/1")
    (CF / "PK_GATE_RESULTS.json").write_text(json.dumps(gate, indent=1) + "\n")
    record = {
        "seq": (sum(1 for _ in ledger_path.open()) if ledger_path.exists() else 0),
        "prev": prev,
        "at": gate["generated_at"],
        "version": version(),
        "verdict": verdict,
        "gate_sha256": sha256_file(CF / "PK_GATE_RESULTS.json"),
        "source_tree_sha256": ident["tree_sha256"],
        "pk_evidence_head": wf.evidence_head if wf else None,
    }
    record["digest"] = sha256_bytes(canonical(record))
    with ledger_path.open("a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
    names = [
        "conformance/PK_GATE_RESULTS.json",
        "conformance/pk_core_gate.json",
        "evidence/pk_evidence.jsonl",
        "evidence/conformance-findings.json",
        "evidence/jobs.json",
        "evidence/benchmark-results.json",
        "evidence/compatibility-results.json",
        "evidence/sbom.cdx.json",
        "evidence/provenance.json",
        "evidence/inv23_release_ledger.jsonl",
    ]
    (EV / "checksums.sha256").write_text("".join(f"{sha256_file(ROOT / n)}  {n}\n" for n in names if (ROOT / n).exists()))
    print(json.dumps({"verdict": verdict, "blockers": blockers, "conditions": conditions}, indent=1))
    return {"GO": 0, "CONDITIONAL_GO": 2, "NO_GO": 3}[verdict]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - an unproducible gate is BLOCKED, never GO
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(4)
