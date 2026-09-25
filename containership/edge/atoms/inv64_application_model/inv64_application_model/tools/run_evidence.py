"""Full conformance / evidence run (MC-02 D04, MC-29, MC-37): one command, machine-readable results.

    python -m inv64_application_model.tools.run_evidence --out evidence/ [--quick] [--certification]
           [--dist DIR] [--release DIR] [--pk-gate FILE] [--approval FILE]

Runs every evidence producer named in ops/GATE_POLICY.json, captures stdout,
stderr, exit status and duration of each into ``<out>/logs/`` and
``<out>/RUN.json`` (environment, tool versions, source revision), then runs the
exit gate. A producer that crashes yields a FAIL evidence file — never a
missing or skipped one. Exit status is the gate's (0 GO, 2 CONDITIONAL_GO, 3 NO_GO).
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent


def _run(name: str, args: list[str], logs: Path, env=None) -> dict:
    t0 = time.time()
    p = subprocess.run([sys.executable, *args], cwd=str(PARENT), capture_output=True, text=True, env=env)
    (logs / f"{name}.log").write_text(f"$ python {' '.join(args)}\nexit={p.returncode}\n--- stdout\n{p.stdout}\n--- stderr\n{p.stderr}",
                                      encoding="utf-8")
    return {"step": name, "exit": p.returncode, "seconds": round(time.time() - t0, 2)}


def _ensure(path: Path, schema: str, step: dict) -> None:
    """A producer that crashed before writing evidence still leaves a FAIL record."""
    if not path.is_file():
        path.write_text(json.dumps({"schema": schema, "result": "FAIL", "reason": f"producer exited {step['exit']} without evidence",
                                    "log": f"logs/{step['step']}.log"}, indent=2) + "\n", encoding="utf-8")


def smoke_audit(out: Path) -> dict:
    """End-to-end smoke through the service with a real ledger, then seal and verify it."""
    sys.path.insert(0, str(PARENT))
    from inv64_application_model.audit import AuditLog, AuditChainBroken
    from inv64_application_model.auth import Authenticator, TrustConfig, mint
    from inv64_application_model.authz import Authorizer
    from inv64_application_model.service import ApplicationModelService
    key, anchor_key = os.urandom(32), os.urandom(32)
    ledger = out / "smoke-audit.jsonl"
    if ledger.exists():
        ledger.unlink()
    audit = AuditLog(ledger, mac_key=key)
    trust = TrustConfig("smoke", "inv64", {"iss": {"k": ("HS256", key)}})
    pol = {"format": "PK_APP_AUTHZ_POLICY/1", "version": "smoke", "grants": [{"id": "g", "roles": ["dev"],
           "capabilities": ["app.submit", "app.validate"], "tenants": ["acme"], "environments": ["prod"], "sites": ["*"], "resources": ["apps/*"]}]}
    svc = ApplicationModelService(authenticator=Authenticator(lambda: trust), authorizer=Authorizer(pol, audit=audit), audit=audit)
    ex = (ROOT / "examples" / "valid.json").read_text()
    now = time.time()
    for i, op in enumerate(["submit", "validate", "submit"]):
        tok = mint({"iss": "iss", "sub": "smoke", "aud": "inv64", "tid": "acme", "kind": "automation", "roles": ["dev"],
                    "iat": now, "exp": now + 300, "jti": f"s{i}"}, kid="k", key=key)
        svc.handle({"format": "PK_APP_SUBMIT_REQUEST/1", "version": "PK_APP_SUBMIT/2", "operation": op, "tenant": "acme",
                    "environment": "prod", "site": "s1", "app": "smoke", "manifest_json": ex,
                    "idempotency_key": "smoke-idempotency-0001"}, token=tok)
    svc.handle({"format": "PK_APP_SUBMIT_REQUEST/1", "version": "PK_APP_SUBMIT/2", "operation": "validate", "tenant": "acme",
                "environment": "prod", "site": "s1", "app": "smoke", "manifest_json": ex}, token="forged")
    anchor = out / "smoke-audit.anchor.json"
    audit.seal(anchor, key=anchor_key)
    try:
        n = AuditLog(ledger, mac_key=key).verify(anchor_path=anchor, anchor_key=anchor_key)
        ops = sorted({r["operation"] for r in audit.records()})
        return {"schema": "PK_APP_AUDIT_VERIFY/1", "ledger": ledger.name, "result": "PASS", "records": n,
                "operations": ops, "note": "ephemeral MAC/anchor keys generated for this run; production keys come from KMS"}
    except AuditChainBroken as e:
        return {"schema": "PK_APP_AUDIT_VERIFY/1", "ledger": ledger.name, "result": "FAIL", "error": str(e)}


def rollback_drill_evidence() -> dict:
    sys.path.insert(0, str(PARENT))
    from inv64_application_model.activation import ConfigStore
    from inv64_application_model.manifest import canonical, validate
    from inv64_application_model.rollout import rollback_drill
    base = json.loads((ROOT / "examples" / "valid.json").read_text())
    mk = lambda tag: {"scope": {"tenant": "drill"}, "manifest": dict(base, **{"x-drill": tag}),
                      "digest": canonical(dict(base, **{"x-drill": tag}))}
    d = tempfile.mkdtemp()
    return rollback_drill(lambda: ConfigStore(d), candidate_effective=mk("candidate"), known_good_effective=mk("known-good"),
                          validator=validate)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "evidence"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--certification", action="store_true", help="kept for CI symmetry; evidence preflight always runs in certification mode")
    ap.add_argument("--dist")
    ap.add_argument("--release")
    ap.add_argument("--pk-gate")
    ap.add_argument("--approval")
    ap.add_argument("--fuzz-iterations", type=int, default=3000)
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    logs = out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    m = "inv64_application_model"
    steps = []
    plan = [
        ("tests", [f"{m}/tests/run_all.py", "--json", str(out / "TESTS.json")], "TESTS.json", "PK_APP_TESTS/1"),
        ("tests_O", ["-O", f"{m}/tests/run_all.py", "--json", str(out / "TESTS_O.json")], "TESTS_O.json", "PK_APP_TESTS/1"),
        ("source", ["-m", f"{m}.tools.source_integrity", "--json"], None, None),
        ("preflight", ["-m", f"{m}.tools.preflight", "--certification", "--out", str(out / "PREFLIGHT.json")], "PREFLIGHT.json", "PK_APP_PREFLIGHT/1"),
        ("secret_scan", ["-m", f"{m}.tools.secret_scan", "--json"], None, None),
        ("fuzz", ["-m", f"{m}.tools.fuzz", "--seed", "64", "--iterations", str(500 if a.quick else a.fuzz_iterations), "--out", str(out / "FUZZ.json")], "FUZZ.json", "PK_APP_FUZZ/1"),
        ("faults", ["-m", f"{m}.tools.faults", "--out", str(out / "FAULTS.json")], "FAULTS.json", "PK_APP_FAULTS/1"),
        ("stress", ["-m", f"{m}.tools.stress", "--profile", "ci", "--out", str(out / "STRESS.json")], "STRESS.json", "PK_APP_STRESS/1"),
        ("perf", ["-m", f"{m}.bench.perf"] + (["--quick"] if a.quick else []) + ["--out", str(out / "PERF.json")], "PERF.json", "PK_APP_PERF/1"),
        ("perf_gate", ["-m", f"{m}.bench.perf", "--compare", str(ROOT / "evidence" / "PERF_BASELINE.json"), "--candidate", str(out / "PERF.json"), "--out", str(out / "PERF_GATE.json")], "PERF_GATE.json", "PK_APP_PERF_GATE/1"),
        ("integration", ["-m", f"{m}.tools.integration", "--out", str(out / "INTEGRATION.json")], "INTEGRATION.json", "PK_APP_INTEGRATION/1"),
        ("integration_real", ["-m", f"{m}.tools.integration", "--profile", "real", "--out", str(out / "INTEGRATION_REAL.json")], "INTEGRATION_REAL.json", "PK_APP_INTEGRATION/1"),
        ("build", ["-m", f"{m}.tools.build_check", "--dist", a.dist or str(out.parent / "_build" / "dist"), "--out", str(out / "BUILD.json")], "BUILD.json", "PK_APP_BUILD/1"),
    ]
    for name, args, fname, schema in plan:
        st = _run(name, args, logs)
        steps.append(st)
        if fname:
            _ensure(out / fname, schema, st)
        if name == "source":
            txt = (logs / "source.log").read_text().split("--- stdout\n", 1)[1].split("\n--- stderr")[0].strip()
            (out / "SOURCE_CHECK.json").write_text(json.dumps(json.loads(txt), indent=2) + "\n")
        if name == "secret_scan":
            txt = (logs / "secret_scan.log").read_text().split("--- stdout\n", 1)[1].split("\n--- stderr")[0].strip()
            (out / "SECRET_SCAN.json").write_text(json.dumps(json.loads(txt), indent=2) + "\n")
    t0 = time.time()
    (out / "AUDIT_VERIFY.json").write_text(json.dumps(smoke_audit(out), indent=2) + "\n")
    (out / "ROLLBACK_DRILL.json").write_text(json.dumps(rollback_drill_evidence(), indent=2) + "\n")
    steps.append({"step": "audit+drill", "exit": 0, "seconds": round(time.time() - t0, 2)})
    gov = _run("governance", ["-m", f"{m}.tools.governance_check", "--json"], logs)
    txt = (logs / "governance.log").read_text().split("--- stdout\n", 1)[1].split("\n--- stderr")[0].strip()
    (out / "GOVERNANCE.json").write_text(json.dumps(json.loads(txt), indent=2) + "\n")
    steps.append(gov)
    rel = Path(a.release) if a.release else out.parent / "_build" / "release"
    dist = a.dist or str(out.parent / "_build" / "dist")
    st = _run("release_build", ["-m", f"{m}.tools.release", "build", "--dist", dist, "--evidence", str(out), "--out", str(rel)], logs)
    steps.append(st)
    st = _run("release_verify", ["-m", f"{m}.tools.release", "verify", "--release", str(rel), "--dist", dist, "--out", str(out / "RELEASE_VERIFY.json")], logs)
    steps.append(st)
    _ensure(out / "RELEASE_VERIFY.json", "PK_APP_RELEASE_VERIFY/1", st)
    try:
        import cryptography
        cv = cryptography.__version__
    except ImportError:
        cv = None
    run = {"schema": "PK_APP_RUN/1", "python": sys.version.split()[0], "executable": sys.executable,
           "platform": platform.platform(), "machine": platform.machine(), "cryptography": cv,
           "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "steps": steps}
    (out / "RUN.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    gate_args = ["-m", f"{m}.release_gate", "--evidence", str(out)]
    if a.pk_gate:
        gate_args += ["--pk-gate", a.pk_gate]
    if a.approval:
        gate_args += ["--approval", a.approval]
    g = _run("gate", gate_args, logs)
    print((logs / "gate.log").read_text().split("--- stdout\n", 1)[1].split("\n--- stderr")[0])
    for s in steps:
        print(f"  {s['step']:18} exit={s['exit']} {s['seconds']}s")
    return g["exit"]


if __name__ == "__main__":
    sys.exit(main())
