"""Items 03, 08, 23: build the machine-readable evidence bundle, traceability
matrix, remediation status register, SBOM, file digests, provenance
statement, signature and the local production gate result.

    python tools/build_release.py            (from the package directory)

Output (all digest-bound):
  evidence/verification/{normal,optimized,strict_core}.json   verify.py runs
  evidence/perf/{baseline,gate}.json                          benchmark + threshold gate
  evidence/host_readback.json                                 real collector read-back of this host
  evidence/governance.json                                    tools/verify_governance.py report
  evidence/ledger.jsonl                                       hash chain over every evidence file
  remediation/STATUS.json, TRACEABILITY.json
  sbom.cdx.json                                               CycloneDX 1.5
  SHA256SUMS.txt                                              every file except release/ and conformance/
  release/provenance.intoto.json                              in-toto v1 statement over SHA256SUMS
  release/signature.json                                      Ed25519 signature (EPHEMERAL DEV KEY)
  conformance/INV43_LOCAL_GATE.json                           explicit GO/NO-GO with digests

The gate can only say GO when governance reports production_ready AND the
strict pk_core run passed AND no item is PARTIAL/BLOCKED.  In 4.3.0 it says
NO_GO, and lists why.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True


def _load(name):
    spec = importlib.util.spec_from_file_location(name, PKG / "tools" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_verify(label: str, args: list[str], env_extra: dict) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **env_extra)
    t = time.time()
    p = subprocess.run([sys.executable, *args, str(PKG / "verify.py")], capture_output=True, text=True, env=env,
                       cwd=str(PKG.parent), timeout=900)
    out = p.stdout + p.stderr
    m = re.search(r"Ran (\d+) tests", out)
    sk = re.search(r"skipped=(\d+)", out)
    fails = re.search(r"failures=(\d+)", out)
    errs = re.search(r"errors=(\d+)", out)
    return {"label": label, "argv": [sys.executable, *args, "verify.py"], "env": env_extra, "exit_code": p.returncode,
            "tests_run": int(m.group(1)) if m else None, "skipped": int(sk.group(1)) if sk else 0,
            "failures": int(fails.group(1)) if fails else 0, "errors": int(errs.group(1)) if errs else 0,
            "started_unix": t, "duration_s": round(time.time() - t, 2), "tail": out.strip().splitlines()[-6:]}


def host_readback() -> dict:
    sys.path.insert(0, str(PKG.parent))
    import importlib
    name = PKG.name
    collector = importlib.import_module(f"{name}.collector")
    rb = collector.collect(collector.local_node_id())
    state, notes = rb.to_state({})  # no measured costs on this host -> actives become unknown
    required = ["spectre_v2", "l1tf", "mds", "mmio_stale_data"]
    try:
        verdict = state.may_cotenant("tenant-a", "tenant-b", required)
    except Exception as exc:  # MitigationMissing
        verdict = exc.to_dict()
    return {"schema": "INV43_HOST_READBACK_EVIDENCE/1", "readback": rb.to_dict(include_monotonic=False),
            "readback_digest": rb.digest(), "downgrade_notes": notes,
            "status_v2": state.report(required, version=2), "cross_tenant_decision_baseline": verdict,
            "interpretation": "Real kernel read-back of the build host. It is an evidence sample for the collector, "
                              "not a certification of any production node."}


def cyclonedx() -> dict:
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                     "component": {"type": "library", "name": "inv43-transient-execution-defense",
                                   "version": (PKG / "VERSION").read_text().strip(),
                                   "licenses": [{"license": {"name": "UNDECIDED - not licensed for redistribution"}}]},
                     "tools": [{"name": "tools/build_release.py"}]},
        "components": [
            {"type": "library", "name": "python-stdlib", "version": platform.python_version(), "scope": "required",
             "description": "runtime dependency: CPython standard library only"},
            {"type": "library", "name": "jsonschema", "version": "4.26.0", "scope": "optional", "purl": "pkg:pypi/jsonschema@4.26.0",
             "licenses": [{"license": {"id": "MIT"}}], "description": "dev/test: Draft 2020-12 schema conformance"},
            {"type": "library", "name": "pk_core", "version": "UNRESOLVED", "scope": "optional",
             "description": "external registry runtime; not present; see deps/pk_core.lock.json"},
        ],
    }


def main() -> int:
    table = _load("status_table")
    gov = _load("verify_governance")
    ev = PKG / "evidence"
    (ev / "verification").mkdir(parents=True, exist_ok=True)
    (PKG / "release").mkdir(exist_ok=True)
    (PKG / "conformance").mkdir(exist_ok=True)
    today = dt.date.today()

    # 1. verification runs
    runs = [run_verify("normal", [], {"INV43_REQUIRE_JSONSCHEMA": "1"}),
            run_verify("optimized", ["-O"], {"INV43_REQUIRE_JSONSCHEMA": "1"}),
            run_verify("strict_core", [], {"PK_REQUIRE_CORE": "1", "INV43_REQUIRE_JSONSCHEMA": "1"})]
    for r in runs:
        (ev / "verification" / f"{r['label']}.json").write_text(json.dumps(r, indent=2))

    # 2. benchmark + gate
    bench = subprocess.run([sys.executable, str(PKG / "bench" / "run_bench.py"), "--gate", "--n", "5000",
                            "--out", str(ev / "perf")], capture_output=True, text=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=900)
    # 3. host read-back
    (ev / "host_readback.json").write_text(json.dumps(host_readback(), indent=2, sort_keys=True))
    # 4. governance
    grep = gov.check(PKG, today)
    (ev / "governance.json").write_text(json.dumps(grep, indent=2, sort_keys=True))

    # 5. status + traceability
    status = {"schema": "INV43_REMEDIATION_STATUS/1", "version": (PKG / "VERSION").read_text().strip(),
              "generated": today.isoformat(), "states": {"LOCAL_IMPLEMENTED": [], "PARTIAL": [], "BLOCKED": []},
              "items": {}}
    md = (PKG / "remediation" / "INV43_v4.2.0_MISSING_COMPONENT_REMEDIATION_CHECKLIST.md").read_text()
    heads = dict(re.findall(r"^## (\d\d)\. (.+)$", md, re.M))
    sev = dict(re.findall(r"^## (\d\d)\..+?\n\n\*\*Severity:\*\* (\w+)", md, re.M | re.S))
    ctl = {}
    for n, c in re.findall(r"^## (\d\d)\..+?\*\*Related controls:\*\* (.+?)\s*$", md, re.M | re.S):
        s = set()
        for a, b in re.findall(r"C(\d{3})(?:-C(\d{3}))?", c):
            s |= {f"C{i:03d}" for i in range(int(a), int(b or a) + 1)}
        ctl[n] = sorted(s)
    for k, (state, evidence, blocked) in table.ITEMS.items():
        status["items"][k] = {"title": heads[k], "severity": sev[k], "controls": ctl.get(k, []), "state": state,
                              "evidence": evidence, "blocked_on": blocked, "independently_reviewed": False}
        status["states"][state].append(k)
    (PKG / "remediation" / "STATUS.json").write_text(json.dumps(status, indent=2))
    checklist = json.loads((PKG / "CHECKLIST.json").read_text())
    trace = {"schema": "INV43_TRACEABILITY/1", "controls": {}}
    for it in checklist["items"]:
        cid = it["check_id"].split("-")[-1]
        items = [k for k, v in status["items"].items() if cid in v["controls"]]
        states = {status["items"][k]["state"] for k in items}
        trace["controls"][it["check_id"]] = {
            "requirement": it["requirement"], "dimension": it["dimension"], "remediation_items": items,
            "evidence": sorted({e for k in items for e in status["items"][k]["evidence"]}
                               | set(table.EXTRA_CONTROLS.get(cid, []))),
            "state": ("BLOCKED" if "BLOCKED" in states else "PARTIAL" if "PARTIAL" in states
                      else "LOCAL_IMPLEMENTED" if states else
                      ("PARTIAL" if any(x.startswith("BLOCKED") for x in table.EXTRA_CONTROLS.get(cid, []))
                       else "LOCAL_IMPLEMENTED")),
        }
    (PKG / "TRACEABILITY.json").write_text(json.dumps(trace, indent=2))

    # 6. SBOM
    (PKG / "sbom.cdx.json").write_text(json.dumps(cyclonedx(), indent=2))

    # 7. evidence ledger (hash chain over evidence files)
    prev = "0" * 64
    lines = []
    for i, p in enumerate(sorted(x for x in ev.rglob("*") if x.is_file() and x.name != "ledger.jsonl")):
        body = {"seq": i, "path": str(p.relative_to(PKG)), "sha256": sha(p)}
        h = hashlib.sha256(prev.encode() + json.dumps(body, sort_keys=True).encode()).hexdigest()
        lines.append(json.dumps({**body, "prev": prev, "hash": h}, sort_keys=True))
        prev = h
    (ev / "ledger.jsonl").write_text("\n".join(lines) + "\n")
    ledger_head = {"seq": len(lines) - 1, "hash": prev}

    # 8. SHA256SUMS over everything except release/ and conformance/
    files = sorted(p for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts
                   and p.relative_to(PKG).parts[0] not in {"release", "conformance"} and p.name != "SHA256SUMS.txt")
    sums = "".join(f"{sha(p)}  ./{p.relative_to(PKG).as_posix()}\n" for p in files)
    (PKG / "SHA256SUMS.txt").write_text(sums)
    sums_digest = sha(PKG / "SHA256SUMS.txt")

    # 9. provenance statement + signature (ephemeral dev key)
    stmt = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": "SHA256SUMS.txt", "digest": {"sha256": sums_digest}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv43/tools/build_release.py@1",
                                              "externalParameters": {"version": status["version"]},
                                              "resolvedDependencies": [{"name": "python", "version": platform.python_version()}]},
                          "runDetails": {"builder": {"id": "claude-cowork-sandbox (not a trusted builder)"},
                                         "metadata": {"finishedOn": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}}}}
    stmt_bytes = json.dumps(stmt, sort_keys=True, separators=(",", ":")).encode()
    (PKG / "release" / "provenance.intoto.json").write_text(json.dumps(stmt, indent=2, sort_keys=True))
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        k = Ed25519PrivateKey.generate()
        sig = k.sign(stmt_bytes)
        pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        signature = {"schema": "INV43_SIGNATURE/1", "algorithm": "Ed25519", "key_class": "EPHEMERAL_DEV_KEY",
                     "warning": "Proves integrity since build only. The private key was discarded; this is NOT a release "
                                "signature and does not prove who built it. Item 23 stays PARTIAL until a release key signs.",
                     "public_key_b64": base64.b64encode(pub).decode(), "signed": "release/provenance.intoto.json (canonical JSON)",
                     "signature_b64": base64.b64encode(sig).decode()}
    except ImportError:
        signature = {"schema": "INV43_SIGNATURE/1", "algorithm": None, "key_class": "NONE",
                     "warning": "cryptography not installed; unsigned"}
    (PKG / "release" / "signature.json").write_text(json.dumps(signature, indent=2))

    # 10. local production gate
    cfg_mod = __import__(f"{PKG.name}.config", fromlist=["x"])
    pol = json.loads((PKG / "policy" / "default_policy.json").read_text())
    strict_ok = runs[2]["exit_code"] == 0
    reasons = []
    if not all(r["exit_code"] == 0 for r in runs[:2]):
        reasons.append("standalone verification failed")
    if not strict_ok:
        reasons.append("PK_REQUIRE_CORE=1 verification failed (pk_core absent - item 02)")
    if not grep["production_ready"]:
        reasons.append(f"governance: {len(grep['blockers'])} blockers, {len(grep['failures'])} failures")
    if status["states"]["BLOCKED"] or status["states"]["PARTIAL"]:
        reasons.append(f"remediation: {len(status['states']['BLOCKED'])} BLOCKED, {len(status['states']['PARTIAL'])} PARTIAL")
    gate = {"schema": "INV43_PRODUCTION_GATE/1", "component": "INV-43", "version": status["version"],
            "verdict": "NO_GO" if reasons else "GO", "reasons": reasons,
            "approver": None, "approver_note": "No approver exists (OWNERS.json unassigned); a GO would require one.",
            "decided_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "release_digest": {"SHA256SUMS.txt": sums_digest},
            "config_digest": cfg_mod.digest(cfg_mod.merge()), "policy_digest": pol["digest"],
            "evidence": {"ledger": "evidence/ledger.jsonl", "ledger_head": ledger_head,
                         "verification": {r["label"]: {"exit_code": r["exit_code"], "tests_run": r["tests_run"],
                                                       "skipped": r["skipped"]} for r in runs},
                         "bench_exit_code": bench.returncode},
            "remediation_counts": {k: len(v) for k, v in status["states"].items()}}
    (PKG / "conformance" / "INV43_LOCAL_GATE.json").write_text(json.dumps(gate, indent=2))
    print(json.dumps(gate, indent=2))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(PKG.parent))
    raise SystemExit(main())
