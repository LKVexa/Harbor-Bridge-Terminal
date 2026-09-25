"""Repository-local certification gate producing machine-readable evidence (MC-01, MC-21.027-.031, MC-23.028-.030).

Result model: every check is PASS / FAIL / SKIP / ERROR.  SKIP and ERROR are
never converted to PASS.  ``certifiable`` is true only when every check is
PASS - which, until the external items (pk_core, real-vsock rows, license and
named owners) are provided, it cannot be.

Exit codes (stable):

====  ==========================================================
0     all checks PASS (certify) / no FAIL or ERROR (local)
1     at least one requirement check FAIL (or SKIP in certify mode)
2     infrastructure ERROR (e.g. pk_core unavailable in certify mode)
3     configuration / usage error
4     evidence document failed schema validation
====  ==========================================================
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Callable

from . import schema_check

PKG = pathlib.Path(__file__).resolve().parent
ROOT = PKG.parent
EXIT_PASS, EXIT_FAIL, EXIT_INFRA, EXIT_CONFIG, EXIT_EVIDENCE = 0, 1, 2, 3, 4
SKIP_DIRS = {".git", "dist", "evidence", "__pycache__", ".mypy_cache", ".ruff_cache", "fuzz-regressions"}
VOLATILE_KEYS = {"generated_at", "duration_s", "deterministic_digest", "environment", "tools", "detail"}


@dataclass
class Check:
    id: str
    requirements: list[str]
    fn: Callable[["Ctx"], tuple[str, str, list[str]]]


@dataclass
class Ctx:
    mode: str
    out: pathlib.Path
    timeout_s: float
    logs: dict[str, str] = field(default_factory=dict)


def source_digest(root: pathlib.Path = PKG) -> str:
    try:
        files = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True,
                               timeout=30).stdout.decode().split("\0")
        files = [f for f in files if f]
    except (OSError, subprocess.SubprocessError):
        files = [p.relative_to(root).as_posix() for p in root.rglob("*")
                 if p.is_file() and not SKIP_DIRS.intersection(p.relative_to(root).parts)]
    h = hashlib.sha256()
    for rel in sorted(files):
        p = root / rel
        if p.is_file():
            h.update(rel.encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def environment() -> dict:
    import cryptography
    from cryptography.hazmat.backends.openssl.backend import backend

    from .vsock import platform_support
    return {"os": platform.system(), "kernel": platform.release(), "machine": platform.machine(),
            "python": platform.python_version(), "implementation": platform.python_implementation(),
            "cryptography": cryptography.__version__, "crypto_backend": backend.openssl_version_text(),
            "build_backend": "setuptools", "vsock": platform_support(), "ci": bool(os.environ.get("CI"))}


def _run(ctx: Ctx, name: str, cmd: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=ctx.timeout_s, cwd=ROOT,
                              env={**os.environ, **(env or {}), "PYTHONPATH": str(ROOT)})
    except subprocess.TimeoutExpired:
        ctx.logs[name] = "TIMEOUT"
        raise
    ctx.logs[name] = proc.stdout[-20000:] + "\n--- stderr ---\n" + proc.stderr[-20000:]
    return proc


def _py(*args: str) -> list[str]:
    return [sys.executable, *args]


def c_wire(ctx: Ctx):
    p = _run(ctx, "wire", _py("-m", "inv36_control_transport.tools.gen_wire", "--check"))
    return ("PASS" if p.returncode == 0 else "FAIL"), p.stdout.strip()[-300:], ["logs/wire.log"]


def _unittest(ctx: Ctx, name: str, opt: bool):
    args = (["-O"] if opt else []) + ["-m", "unittest", "discover", "-s", str(PKG / "tests"), "-t", str(PKG / "tests")]
    p = _run(ctx, name, _py(*args))
    tail = p.stderr.strip().splitlines()[-3:]
    m = re.search(r"Ran (\d+) tests", p.stderr)
    skipped = re.search(r"skipped=(\d+)", p.stderr)
    detail = f"ran={m.group(1) if m else '?'} skipped={skipped.group(1) if skipped else 0} :: {' '.join(tail)}"
    return ("PASS" if p.returncode == 0 else "FAIL"), detail, [f"logs/{name}.log"]


def c_unit(ctx: Ctx):
    return _unittest(ctx, "unit", False)


def c_unit_opt(ctx: Ctx):
    return _unittest(ctx, "unit_optimized", True)


def c_fuzz(ctx: Ctx):
    iters = "2000" if ctx.mode == "certify" else "300"
    p = _run(ctx, "fuzz", _py("-m", "inv36_control_transport.tools.fuzz", "--iterations", iters, "--seed",
                              os.environ.get("INV36_FUZZ_SEED", "1"), "--out", str(ctx.out / "fuzz.json")))
    return ("PASS" if p.returncode == 0 else "FAIL"), p.stdout.strip()[-300:], ["fuzz.json"]


def c_trace(ctx: Ctx):
    p = _run(ctx, "traceability", _py("-m", "inv36_control_transport.tools.traceability", "--check"))
    return ("PASS" if p.returncode == 0 else "FAIL"), p.stdout.strip()[-600:], ["logs/traceability.log"]


def c_mc(ctx: Ctx):
    p = _run(ctx, "mc_status", _py("-m", "inv36_control_transport.tools.mc_status", "--check"))
    return ("PASS" if p.returncode == 0 else "FAIL"), p.stdout.strip()[-600:], ["logs/mc_status.log"]


def c_docs(ctx: Ctx):
    p = _run(ctx, "docs", _py("-m", "inv36_control_transport.tools.docs_check"))
    return ("PASS" if p.returncode == 0 else "FAIL"), p.stdout.strip()[-600:], ["logs/docs.log"]


def c_secrets(ctx: Ctx):
    p = _run(ctx, "secrets", _py("-m", "inv36_control_transport.tools.secret_scan"))
    return ("PASS" if p.returncode == 0 else "FAIL"), p.stdout.strip()[-300:], ["logs/secrets.log"]


def c_perf(ctx: Ctx):
    cand = ctx.out / "bench.json"
    p = _run(ctx, "bench", _py("-m", "inv36_control_transport.tools.bench", "--profile",
                               "full" if ctx.mode == "certify" else "smoke", "--out", str(cand)))
    if p.returncode != 0:
        return "ERROR", "benchmark crashed", ["logs/bench.log"]
    c = _run(ctx, "bench_compare", _py("-m", "inv36_control_transport.tools.bench", "--compare",
                                       str(PKG / "perf" / "baseline-reference.json"), str(cand)))
    return ("PASS" if c.returncode == 0 else "FAIL"), c.stdout.strip()[-600:], ["bench.json",
                                                                                "logs/bench_compare.log"]


def c_governance(ctx: Ctx):
    gov = json.loads((PKG / "governance" / "owners.json").read_text())
    missing = [r for r, v in gov["roles"].items() if not v.get("name") or v["name"].startswith("UNASSIGNED")]
    problems = []
    if not (PKG / "LICENSE").exists():
        problems.append("LICENSE absent (owner/legal decision pending, MC-22)")
    if missing:
        problems.append(f"unassigned roles: {', '.join(missing)}")
    expired = [w["id"] for w in json.loads((PKG / "governance" / "waivers.json").read_text())["waivers"]
               if w.get("expires") and w["expires"] < _dt.date.today().isoformat()]
    if expired:
        problems.append(f"expired waivers: {expired}")
    return ("FAIL" if problems else "PASS"), "; ".join(problems) or "owners, license and waivers in order", \
        ["governance/owners.json", "governance/waivers.json"]


def c_vsock(ctx: Ctx):
    from .vsock import platform_support
    info = platform_support()
    if not info["dev_vsock"]:
        return "SKIP", f"no vsock device ({info['tier']})", []
    p = _run(ctx, "vsock_smoke", _py("-m", "inv36_control_transport.tools.vsock_smoke", "--out",
                                     str(ctx.out / "vsock-smoke.json")))
    data = json.loads((ctx.out / "vsock-smoke.json").read_text()) if (ctx.out / "vsock-smoke.json").exists() else {}
    if p.returncode != 0:
        return "FAIL", p.stdout.strip()[-400:], ["vsock-smoke.json"]
    # A kernel-path smoke without an end-to-end peer is not a full real-vsock certification.
    status = "PASS" if data.get("end_to_end") else "SKIP"
    return status, data.get("summary", "")[:400], ["vsock-smoke.json"]


def c_vuln(ctx: Ctx):
    import shutil
    if not shutil.which("pip-audit"):
        return "SKIP", "pip-audit not installed here; CI job 'security' runs it", []
    p = _run(ctx, "pip_audit", ["pip-audit", "-r", str(PKG / "requirements.txt"), "-f", "json"])
    return ("PASS" if p.returncode == 0 else "FAIL"), p.stdout[-300:], ["logs/pip_audit.log"]


def c_pkcore(ctx: Ctx):
    from .pkcore_adapter import GateUnavailable, probe, run_gate
    info = probe()
    if info["status"] != "available":
        status = "ERROR" if ctx.mode == "certify" else "SKIP"
        return status, f"pk_core {info['status']}: {info.get('reason')}", []
    try:
        res = run_gate(timeout_s=ctx.timeout_s)
    except GateUnavailable as exc:
        return "ERROR", json.dumps(exc.to_dict())[:400], []
    (ctx.out / "pk_core.json").write_text(json.dumps(res, indent=1))
    return ("PASS" if res["normalized"]["all_pass"] else "FAIL"), json.dumps(res["normalized"]["statuses"]), \
        ["pk_core.json"]


CHECKS = [
    Check("G01-wire-codegen", ["INV36-REQ-040"], c_wire),
    Check("G02-unit-tests", ["INV36-REQ-001..048 (see traceability)"], c_unit),
    Check("G03-unit-tests-optimized", ["INV36-REQ-005", "INV36-REQ-044"], c_unit_opt),
    Check("G04-fuzz-bounded", ["INV36-REQ-044"], c_fuzz),
    Check("G05-traceability", ["INV36-REQ-048", "INV-36-C020"], c_trace),
    Check("G06-mc-ledger", ["INV-36-C099"], c_mc),
    Check("G07-docs-consistency", ["INV36-REQ-040"], c_docs),
    Check("G08-secret-scan", ["INV36-REQ-015"], c_secrets),
    Check("G09-performance", ["INV36-REQ-035", "INV36-REQ-036", "INV36-REQ-037"], c_perf),
    Check("G10-governance-license", ["INV36-REQ-048", "INV-36-C009", "INV-36-C100"], c_governance),
    Check("G11-real-vsock", ["INV36-REQ-001"], c_vsock),
    Check("G12-dependency-vulns", ["INV36-REQ-042"], c_vuln),
    Check("G13-pk_core-estate-gate", ["INV36-REQ-043"], c_pkcore),
]


def references() -> dict:
    """Bind evidence to the ADR revision and the frozen requirements baseline (MC-19.018, MC-20.025)."""
    adr = (PKG / "docs" / "ADR-0001.md").read_text()
    rev = re.search(r"\| Revision \| (\d+)", adr)
    req = (PKG / "requirements" / "requirements.json").read_bytes()
    return {"adr": f"ADR-0001 rev {rev.group(1) if rev else '?'}",
            "adr_sha256": hashlib.sha256(adr.encode()).hexdigest(),
            "requirements_baseline": json.loads(req)["baseline"],
            "requirements_sha256": hashlib.sha256(req).hexdigest(),
            "idl_sha256": hashlib.sha256((PKG / "schema" / "pk_ctrl.idl.json").read_bytes()).hexdigest()}


def _deterministic(doc: dict) -> str:
    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in VOLATILE_KEYS}
        if isinstance(o, list):
            return [strip(x) for x in o]
        return o
    return hashlib.sha256(json.dumps(strip(doc), sort_keys=True).encode()).hexdigest()


def run(mode: str = "local", out: pathlib.Path | None = None, timeout_s: float = 900.0,
        only: list[str] | None = None, artifact_digest: str | None = None) -> tuple[int, dict]:
    if mode not in ("local", "certify"):
        return EXIT_CONFIG, {"error": "mode must be local or certify"}
    out = out or (PKG / "evidence" / _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(mode, out, timeout_s)
    results = []
    for chk in CHECKS:
        if only and chk.id not in only:
            continue
        t0 = time.monotonic()
        try:
            status, detail, ev = chk.fn(ctx)
        except subprocess.TimeoutExpired:
            status, detail, ev = "ERROR", f"timed out after {timeout_s}s", []
        except Exception as exc:  # noqa: BLE001 - a crashing check is an ERROR, never a PASS
            status, detail, ev = "ERROR", f"{type(exc).__name__}: {str(exc)[:300]}", []
        results.append({"id": chk.id, "status": status, "requirements": chk.requirements, "evidence": ev,
                        "detail": detail[:4000], "duration_s": round(time.monotonic() - t0, 3)})
    logs = out / "logs"
    logs.mkdir(exist_ok=True)
    for name, text in ctx.logs.items():
        (logs / f"{name}.log").write_text(text)
    summary = {s: sum(1 for r in results if r["status"] == s) for s in ("PASS", "FAIL", "SKIP", "ERROR")}
    summary["certifiable"] = summary["PASS"] == len(results) and len(results) == len(CHECKS)
    if mode == "certify":
        code = EXIT_INFRA if summary["ERROR"] else (EXIT_FAIL if summary["FAIL"] or summary["SKIP"] else EXIT_PASS)
    else:
        code = EXIT_INFRA if summary["ERROR"] else (EXIT_FAIL if summary["FAIL"] else EXIT_PASS)
    from .pkcore_adapter import probe
    doc = {
        "schema": "inv36.gate-evidence/1", "component": "INV-36", "version": (PKG / "VERSION").read_text().strip(),
        "mode": mode, "source_digest": source_digest(), "artifact_digest": artifact_digest,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "environment": environment(), "tools": {"gate": "inv36.gate/1", "python": platform.python_version()},
        "results": results, "summary": summary, "exit_code": code, "estate": probe(),
        "references": references(),
        "deterministic_digest": "0" * 64,
    }
    doc["deterministic_digest"] = _deterministic(doc)
    try:
        schema_check.validate(doc, schema_check.load("gate-evidence.schema.json"))
    except schema_check.SchemaViolation as exc:
        (out / "gate-evidence.INVALID.json").write_text(json.dumps(doc, indent=1, default=str))
        return EXIT_EVIDENCE, {"error": str(exc)}
    path = out / "gate-evidence.json"
    path.write_text(json.dumps(doc, indent=1, sort_keys=True))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / "gate-evidence.json.sha256").write_text(f"{digest}  gate-evidence.json\n")
    for p in out.rglob("*"):
        if p.is_file():
            os.chmod(p, 0o444)  # preserve raw output read-only for audit review (MC-01.013)
    return code, doc
