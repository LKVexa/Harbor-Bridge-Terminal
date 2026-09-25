"""Release tooling: digests, SBOM, SAST/secret scan, RTM check, evidence manifest, production exit gate
(WS 15, 16, 17, 20).

    python -m inv32_elastic_virtualization.release digests
    python -m inv32_elastic_virtualization.release sbom --out sbom.cdx.json
    python -m inv32_elastic_virtualization.release sast
    python -m inv32_elastic_virtualization.release rtm-check
    python -m inv32_elastic_virtualization.release evidence --out manifest.json [--tests R.json] [--bench B.json]
    python -m inv32_elastic_virtualization.release verify-evidence --manifest manifest.json
    python -m inv32_elastic_virtualization.release gate --manifest manifest.json

Signing: the manifest is signed with HMAC-SHA256 using the key in ``$INV32_RELEASE_KEY`` (reference only).
Keyless/asymmetric provenance (Sigstore/in-toto SLSA) needs the organisation's CI identity -- BLOCKED; the gate
reports ``provenance_signature: reference-hmac`` as a failure reason for production certification.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any

from . import __version__

PKG = Path(__file__).resolve().parent
ROOT = PKG.parent
EXCLUDE_DIRS = {"__pycache__", ".git", "evidence", "dist", "build", ".venv"}
SHIPPED_SUFFIXES = {".py", ".json", ".md", ".service"}


def _files(base: Path = PKG) -> list[Path]:
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_file() and not (set(p.relative_to(base).parts) & EXCLUDE_DIRS) and p.suffix in SHIPPED_SUFFIXES \
                and p.name != "RELEASE_DIGESTS.json":
            out.append(p)
    return out


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def digests() -> dict[str, Any]:
    doc = {"schema": "PK_INV32_RELEASE_DIGESTS/1", "version": __version__,
           "files": {str(p.relative_to(PKG)): sha256(p) for p in _files()
                     if not str(p.relative_to(PKG)).startswith("tests/")
                     and (p.suffix == ".py" or p.parent.name in ("schemas", "conformance"))}}
    (PKG / "RELEASE_DIGESTS.json").write_text(json.dumps(doc, indent=1, sort_keys=True))
    return doc


def sbom() -> dict[str, Any]:
    comps = [{"type": "file", "name": str(p.relative_to(PKG)), "hashes": [{"alg": "SHA-256", "content": sha256(p)}]}
             for p in _files()]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                         "component": {"type": "library", "name": "inv32-elastic-virtualization",
                                       "version": __version__, "licenses": [{"license": {"name": "UNDECIDED (BLOCKED)"}}]}},
            "components": comps,
            "dependencies": [{"ref": "inv32-elastic-virtualization", "dependsOn": []}],
            "properties": [{"name": "runtime-dependencies", "value": "python stdlib only"},
                           {"name": "optional-dependencies", "value": "pk_core>=1.0,<2.0 (extra: inventory; unpinned, BLOCKED)"}]}


_BANNED_CALLS = {("os", "system"), ("os", "popen"), ("subprocess", "Popen"), ("subprocess", "call"),
                 ("subprocess", "run"), ("subprocess", "check_output"), ("pickle", "loads"), ("marshal", "loads")}
_BANNED_NAMES = {"eval", "exec", "compile", "__import__"}
_SECRET_RE = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,})")
SAST_ALLOW = {"release.py": {"subprocess.run"}}  # git rev-parse with fixed argv, no shell


def sast() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for p in _files():
        rel = str(p.relative_to(PKG))
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in _SECRET_RE.finditer(text):
            findings.append({"file": rel, "rule": "secret", "match": m.group(0)[:12] + "…"})
        if p.suffix != ".py" or rel.startswith("tests/"):
            continue
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                name = None
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                    name = (f.value.id, f.attr)
                    if name in _BANNED_CALLS and f"{name[0]}.{name[1]}" not in SAST_ALLOW.get(rel, set()):
                        findings.append({"file": rel, "line": node.lineno, "rule": "banned-call", "call": ".".join(name)})
                elif isinstance(f, ast.Name) and f.id in _BANNED_NAMES:
                    findings.append({"file": rel, "line": node.lineno, "rule": "banned-builtin", "call": f.id})
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        findings.append({"file": rel, "line": node.lineno, "rule": "shell=True"})
    return {"schema": "PK_INV32_SAST/1", "pass": not findings, "findings": findings}


def rtm_check(rtm_path: Path | None = None, *, source_pkg: Path | None = None) -> dict[str, Any]:
    """Validate the RTM against a *source tree* (tests and repo-level files are not shipped in the wheel)."""
    pkg = source_pkg or PKG
    root = pkg.parent
    rtm_path = rtm_path or pkg / "RTM.json"
    rtm = json.loads(rtm_path.read_text())
    errors, ids = [], set()
    test_names = set()
    for tf in (pkg / "tests").glob("test_*.py"):
        for node in ast.walk(ast.parse(tf.read_text())):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                test_names.add(f"{tf.stem}::{node.name}")
    counts: dict[str, int] = {}
    for row in rtm["rows"]:
        rid = row["id"]
        if rid in ids:
            errors.append(f"{rid}: duplicate id")
        ids.add(rid)
        counts[row["status"]] = counts.get(row["status"], 0) + 1
        mandatory = row.get("priority", "P0") in ("P0", "P1")
        if row["status"] in ("IMPLEMENTED", "PARTIAL"):
            if mandatory and not row.get("implementation"):
                errors.append(f"{rid}: mandatory requirement without implementation reference")
            if mandatory and not row.get("tests") and not row.get("manual_approval"):
                errors.append(f"{rid}: mandatory requirement without automated verification")
        for ref in row.get("implementation", []) + row.get("docs", []):
            path = ref.split("::")[0]
            if not (pkg / path).exists() and not (root / path).exists():
                errors.append(f"{rid}: referenced file missing: {path}")
        for t in row.get("tests", []):
            if t not in test_names:
                errors.append(f"{rid}: referenced test missing: {t}")
        if row["status"] == "BLOCKED" and not row.get("blocker"):
            errors.append(f"{rid}: BLOCKED without blocker")
    return {"schema": "PK_INV32_RTM_CHECK/1", "pass": not errors, "errors": errors[:200], "rows": len(rtm["rows"]),
            "status_counts": counts}


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else "UNAVAILABLE: not a git checkout"
    except (OSError, subprocess.SubprocessError):
        return "UNAVAILABLE: git not installed"


def _sign(doc: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, json.dumps(doc, sort_keys=True, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()


def evidence(out: Path, *, tests: Path | None, bench: Path | None, artifacts: list[Path]) -> dict[str, Any]:
    from .validation import SCHEMA_FILES
    from .config import CONFIG_SCHEMA
    sb = sbom()
    sb_bytes = json.dumps(sb, sort_keys=True).encode()
    lock = ROOT / "requirements.lock"
    doc: dict[str, Any] = {
        "schema": "PK_INV32_EVIDENCE/1", "release_version": __version__, "source_commit": _git_commit(),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "builder_identity": os.environ.get("INV32_BUILDER", "UNATTESTED local build"),
        "artifact_digests": {p.name: sha256(p) for p in artifacts if p.exists()},
        "sbom_sha256": hashlib.sha256(sb_bytes).hexdigest(),
        "dependency_lock_sha256": sha256(lock) if lock.exists() else None,
        "schemas": {k: sha256(PKG / "schemas" / v) for k, v in SCHEMA_FILES.items()},
        "config_schema": CONFIG_SCHEMA,
        "compat_matrix_sha256": sha256(PKG / "compat_matrix.json"),
        "rtm_sha256": sha256(PKG / "RTM.json") if (PKG / "RTM.json").exists() else None,
        "test_results": json.loads(tests.read_text()) if tests and tests.exists() else None,
        "benchmark": ({"sha256": sha256(bench), "slo": json.loads(bench.read_text()).get("slo")}
                      if bench and bench.exists() else None),
        "security_scan": sast(),
        "rtm_check": rtm_check() if (PKG / "RTM.json").exists() else None,
        "approvals": [],
        "provenance_signature": "reference-hmac",
    }
    key = os.environ.get("INV32_RELEASE_KEY", "").encode()
    doc["signature"] = _sign(doc, key) if len(key) >= 32 else None
    out.write_text(json.dumps(doc, indent=1, sort_keys=True))
    (out.parent / "sbom.cdx.json").write_text(json.dumps(sb, indent=1, sort_keys=True))
    return doc


def verify_evidence(manifest: Path) -> bool:
    doc = json.loads(manifest.read_text())
    sig = doc.pop("signature", None)
    key = os.environ.get("INV32_RELEASE_KEY", "").encode()
    return bool(sig) and len(key) >= 32 and hmac.compare_digest(sig, _sign(doc, key))


def gate(manifest: Path, *, now: float | None = None) -> dict[str, Any]:
    now = time.time() if now is None else now
    doc = json.loads(manifest.read_text())
    reasons: list[str] = []
    gov = json.loads((PKG / "governance.json").read_text())
    waivers = json.loads((PKG / "waivers.json").read_text())["waivers"]
    rtm = json.loads((PKG / "RTM.json").read_text())
    if any(v is None for v in gov["owners"].values()):
        reasons.append("ownership: accountable owners not named")
    if not verify_evidence(manifest):
        reasons.append("evidence manifest signature missing/invalid")
    if doc.get("provenance_signature") != "slsa-v1":
        reasons.append("provenance: no attested (SLSA/Sigstore) build provenance")
    if not doc.get("source_commit", "").strip() or doc["source_commit"].startswith("UNAVAILABLE"):
        reasons.append("provenance: source commit unavailable")
    matrix = json.loads((PKG / "compat_matrix.json").read_text())
    if not any(r["status"] == "supported" and r["scope"] == "production" for r in matrix["rows"]):
        reasons.append("compatibility: no supported production provider/hypervisor combination")
    tr = doc.get("test_results") or {}
    if not tr or tr.get("failures", 1) or tr.get("errors", 1):
        reasons.append("tests: mandatory suites not green or results missing")
    if not (doc.get("security_scan") or {}).get("pass"):
        reasons.append("security scan failed")
    rc = doc.get("rtm_check") or {}
    if not rc.get("pass"):
        reasons.append("RTM check failed")
    open_p0 = [r["id"] for r in rtm["rows"] if r.get("priority") == "P0" and r["status"] in ("BLOCKED", "PARTIAL")
               and not any(w.get("requirement") == r["id"] and w.get("expires_at", 0) > now for w in waivers)]
    if open_p0:
        reasons.append(f"requirements: {len(open_p0)} P0 items BLOCKED/PARTIAL without waiver")
    expired = [w["id"] for w in waivers if w.get("expires_at", 0) <= now]
    if expired:
        reasons.append(f"waivers expired: {expired}")
    b = doc.get("benchmark") or {}
    if not b or not all(v.get("pass") for v in (b.get("slo") or {}).values()):
        reasons.append("performance: benchmark evidence missing or SLO failed")
    if not any(r for r in rtm["rows"] if r["id"].startswith("CL-19") and r["status"] == "IMPLEMENTED" and
               "exercised" in r.get("note", "")):
        reasons.append("operations: runbooks/emergency-disable rehearsal not exercised in an environment")
    if not doc.get("approvals"):
        reasons.append("approvals: no protected production approval recorded")
    return {"schema": "PK_INV32_EXIT_GATE/1", "result": "PASS" if not reasons else "FAIL", "reasons": reasons,
            "open_p0": open_p0[:50], "evaluated_at": now, "release_version": doc.get("release_version")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="inv32-release")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("digests")
    s = sub.add_parser("sbom")
    s.add_argument("--out", required=True)
    sub.add_parser("sast")
    r = sub.add_parser("rtm-check")
    r.add_argument("--rtm")
    e = sub.add_parser("evidence")
    e.add_argument("--out", required=True)
    e.add_argument("--tests")
    e.add_argument("--bench")
    e.add_argument("--artifact", action="append", default=[])
    v = sub.add_parser("verify-evidence")
    v.add_argument("--manifest", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--manifest", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "digests":
        print(json.dumps({"files": len(digests()["files"])}))
        return 0
    if a.cmd == "sbom":
        Path(a.out).write_text(json.dumps(sbom(), indent=1, sort_keys=True))
        return 0
    if a.cmd == "sast":
        res = sast()
        print(json.dumps(res, indent=1))
        return 0 if res["pass"] else 1
    if a.cmd == "rtm-check":
        res = rtm_check(Path(a.rtm) if a.rtm else None)
        print(json.dumps(res, indent=1))
        return 0 if res["pass"] else 1
    if a.cmd == "evidence":
        evidence(Path(a.out), tests=Path(a.tests) if a.tests else None, bench=Path(a.bench) if a.bench else None,
                 artifacts=[Path(x) for x in a.artifact])
        return 0
    if a.cmd == "verify-evidence":
        ok = verify_evidence(Path(a.manifest))
        print(json.dumps({"valid": ok}))
        return 0 if ok else 1
    res = gate(Path(a.manifest))
    print(json.dumps(res, indent=1))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
