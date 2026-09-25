"""Fail-closed release gate for INV-35 (v4.3.0) — see docs/operations/RELEASE_AND_SUPPLY_CHAIN.md.

Exit codes (unchanged contract from 4.2.0, stricter meaning):
  0 - VERIFY=PASS    every technical and production gate satisfied (production-green)
  1 - VERIFY=FAIL    a technical check failed (compile, schema drift, tests, RTM, manifest, perf)
  2 - VERIFY=PARTIAL technical checks pass but production blockers remain (skipped mandatory
                     tests / pk_core, governance, unsealed evidence, rollout not exercised)
"""
from __future__ import annotations

import compileall
import datetime as dt
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))


def _run(args: list[str]) -> tuple[int, str]:
    r = subprocess.run([sys.executable, *args], cwd=str(ROOT), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def _tests() -> dict[str, object]:
    stream = io.StringIO()
    suite = unittest.TestLoader().discover(str(ROOT / "tests"), top_level_dir=str(ROOT / "tests"))
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    sys.stdout.write(stream.getvalue()[-2000:])
    return {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "skipped_names": [str(t) for t, _ in result.skipped],
            "ok": result.wasSuccessful()}


def _nexus_manifest(release) -> dict[str, object]:
    files = {}
    for sub in ("schemas", "fixtures"):
        for p in sorted((ROOT / sub).rglob("*.json")):
            files[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"schema": "INV35_NEXUS_SPEC/1", "adr": "docs/adr/ADR-0001-separate-orchestration-and-bulk-data-channels.md",
            "interfaces": ["PK_VIRTQUEUE_SUBMIT/1", "PK_VIRTQUEUE_COMPLETE/1", "INV35_ERROR/1", "INV35_STATUS/1",
                           "INV35_CONFIG/1"],
            "conformance_rule": "a backend claiming Nexus conformance reproduces every fixture's expected code",
            "files": files, "digest": hashlib.sha256(release.canonical(files)).hexdigest(),
            "approval": "pending"}


def main() -> int:
    extra = os.environ.get("PK_CORE_PATH")
    if extra and extra not in sys.path:
        sys.path.insert(0, extra)
    release = importlib.import_module(ROOT.name + ".runtime.release")
    version = (ROOT / "VERSION").read_text().strip()
    gates: dict[str, dict[str, object]] = {}
    technical_fail: list[str] = []

    ok = compileall.compile_dir(str(ROOT), quiet=1)
    gates["G1_compile"] = {"ok": bool(ok)}
    if not ok:
        technical_fail.append("compileall")

    rc, out = _run(["tools/gen_schemas.py", "--check"])
    gates["G2_schemas"] = {"ok": rc == 0, "detail": out}
    if rc:
        technical_fail.append("schema_drift")

    t = _tests()
    gates["G3_tests"] = {"ok": t["ok"], **t}
    if not t["ok"]:
        technical_fail.append("tests")

    rc, out = _run(["tools/build_rtm.py", "--check"])
    gates["G4_rtm"] = {"ok": rc == 0, "detail": out}
    if rc:
        technical_fail.append("rtm")

    gates["G5_performance"] = {"ok": t["ok"], "detail": "tests/performance/test_perf_gate.py (part of G3)"}

    manifest = release.build_manifest()
    problems = release.verify_manifest(manifest)
    sbom, prov = release.build_sbom(manifest), release.build_provenance(manifest)
    nexus = _nexus_manifest(release)
    for rel, doc in (("release/manifest/MANIFEST.json", manifest), ("release/sbom/sbom.cdx.json", sbom),
                     ("release/provenance/provenance.intoto.json", prov), ("release/NEXUS_SPEC_MANIFEST.json", nexus)):
        (ROOT / rel).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / rel).write_text(json.dumps(doc, indent=2) + "\n")
    gates["G6_supply_chain"] = {"ok": not problems, "tree_digest": manifest["tree_digest"], "problems": problems,
                                "files": len(manifest["files"])}
    if problems:
        technical_fail.append("manifest")

    blockers: list[dict[str, str]] = []
    if t["skipped"]:
        blockers.append({"gate": "tests", "severity": "blocker", "detail": f"{t['skipped']} mandatory test(s) skipped"})
    if importlib.util.find_spec("pk_core") is None:
        blockers.append({"gate": "pk_core", "severity": "blocker",
                         "detail": "pk_core not importable: set PK_CORE_PATH or install the approved pinned pk_core"})
    gov = release.governance_findings()
    blockers.extend(gov)
    if not (ROOT / "evidence" / f"rollout-{version}.json").is_file():
        blockers.append({"gate": "rollout", "severity": "blocker",
                         "detail": f"canary/rollback drill evidence evidence/rollout-{version}.json absent (G13)"})
    for key in ("G7_ownership", "G8_license", "G9_approvals", "G10_waivers_reviews", "G11_dependencies"):
        gate = {"G7_ownership": "ownership", "G8_license": "license", "G9_approvals": "approval",
                "G10_waivers_reviews": ("waiver", "review"), "G11_dependencies": "dependency"}[key]
        gate = gate if isinstance(gate, tuple) else (gate,)
        found = [b["detail"] for b in gov if b["gate"] in gate]
        gates[key] = {"ok": not found, "findings": found}

    verdict = "FAIL" if technical_fail else ("PARTIAL" if blockers else "PASS")
    document = {"schema": "INV35_GATE_RESULTS/1", "version": version, "verdict": verdict,
                "tree_digest": manifest["tree_digest"], "environment": release.environment_record(),
                "gates": gates, "blockers": blockers + [{"gate": "technical", "severity": "fail", "detail": f}
                                                        for f in technical_fail],
                "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    seal = release.seal(document)
    gates["G12_sealed"] = {"ok": seal["sealed"]}
    if not seal["sealed"] and verdict == "PASS":
        verdict = "PARTIAL"
        document["verdict"] = verdict
        document["blockers"].append({"gate": "seal", "severity": "blocker", "detail": seal["reason"]})
        seal = release.seal(document)
    elif not seal["sealed"]:
        document["blockers"].append({"gate": "seal", "severity": "blocker", "detail": seal["reason"]})
        seal = release.seal(document)
    document["seal"] = seal
    (ROOT / "conformance").mkdir(exist_ok=True)
    (ROOT / "evidence").mkdir(exist_ok=True)
    text = json.dumps(document, indent=2) + "\n"
    (ROOT / "conformance" / "PK_GATE_RESULTS.json").write_text(text)
    (ROOT / "evidence" / f"gate-{version}.json").write_text(text)

    n_block = len([b for b in document["blockers"] if b["severity"] == "blocker"])
    if verdict == "FAIL":
        print(f"VERIFY=FAIL reason={','.join(technical_fail)}")
        return 1
    if verdict == "PARTIAL":
        print(f"VERIFY=PARTIAL tests={t['run']} skipped={t['skipped']} blockers={n_block} "
              f"tree={manifest['tree_digest'][:12]} see=conformance/PK_GATE_RESULTS.json")
        return 2
    print(f"VERIFY=PASS tests={t['run']} tree={manifest['tree_digest'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
