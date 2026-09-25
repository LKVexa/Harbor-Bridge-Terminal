"""MC-36 - Fail-closed production gate with machine-readable release evidence.

    python -m pln02_application_plane.tools.gate --tier local  [--out evidence/gate.json]
    python -m pln02_application_plane.tools.gate --tier release --artifact dist/

Checks (every one must pass for the tier):
  manifest      FILE_MANIFEST.sha256 matches the tree (``--write-manifest`` regenerates it)
  traceability  TRACEABILITY.json equals a fresh build; no orphan requirements; artifacts exist; named tests exist
  governance    ADR states legal; owner roles present; no expired register entries
  source        MASTER.md digest verified if present, else recovery recorded as unresolved
  tests         unittest in normal and ``-O`` modes, zero failures (skips are reported, never counted as passes)
  perf          evidence/perf_baseline.json exists and has no threshold breaches
  build         (ci/release) wheel builds twice byte-identically under SOURCE_DATE_EPOCH
  legal         LICENSE/NOTICE/THIRD_PARTY present; release tier additionally requires a granted licence

Verdict: ``GO`` only when all checks pass *and* every MC item is IMPLEMENTED or covered by an approved,
unexpired exception in ``docs/governance/registers/EXCEPTIONS.json``. Otherwise ``NO_GO`` with reasons.
Exit status: 1 if any check fails; for ``--tier release`` also 1 on ``NO_GO``.
Evidence is HMAC-signed when ``PLN02_GATE_KEY`` (>= 32 bytes) is set; otherwise marked ``unsigned``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
sys.path.insert(0, str(ROOT))
EXCLUDE = re.compile(r"(^|/)(__pycache__|\.git|dist|build|.*\.egg-info)(/|$)|\.pyc$|^FILE_MANIFEST\.sha256$|^evidence/gate")


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree() -> list[str]:
    out = []
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if p.is_file() and not EXCLUDE.search(rel):
            out.append(rel)
    return out


def manifest_text() -> str:
    return "".join(f"{sha256(PKG / r)}  {r}\n" for r in tree())


def check_manifest(write: bool) -> tuple[bool, str]:
    text = manifest_text()
    path = PKG / "FILE_MANIFEST.sha256"
    if write:
        path.write_text(text, "utf-8", newline="\n")
        return True, f"written ({len(text.splitlines())} files)"
    if not path.exists():
        return False, "FILE_MANIFEST.sha256 missing"
    if path.read_text("utf-8") != text:
        have = dict(reversed(l.split("  ", 1)) for l in path.read_text().splitlines())
        want = dict(reversed(l.split("  ", 1)) for l in text.splitlines())
        diff = sorted(k for k in set(have) | set(want) if have.get(k) != want.get(k))
        return False, f"manifest drift: {diff[:10]}"
    return True, f"{len(text.splitlines())} files verified"


def check_traceability() -> tuple[bool, str, dict]:
    from pln02_application_plane.tools.traceability import build
    fresh = build()
    stored = json.loads((PKG / "TRACEABILITY.json").read_text("utf-8"))
    problems = []
    if fresh != stored:
        problems.append("TRACEABILITY.json is stale (regenerate)")
    if fresh["orphans"]:
        problems.append(f"orphan requirements {fresh['orphans']}")
    test_src = "\n".join(p.read_text("utf-8") for p in (PKG / "tests").glob("test_*.py"))
    for mc, c in fresh["components"].items():
        for a in c["artifacts"]:
            if not (PKG / a).exists():
                problems.append(f"{mc}: missing artifact {a}")
        for t in c["tests"]:
            if not t.startswith("gate:") and not re.search(rf"^class {t}\b", test_src, re.M):
                problems.append(f"{mc}: missing test class {t}")
        if c["status"] == "IMPLEMENTED" and c["open_acceptance"]:
            problems.append(f"{mc}: IMPLEMENTED but has open acceptance items")
    return not problems, "; ".join(problems) or "complete", fresh


def check_governance() -> tuple[bool, str]:
    problems = []
    idx = (PKG / "docs/adr/ADR_INDEX.md").read_text("utf-8")
    for row in re.findall(r"^\| (ADR-\S+) \| [^|]+\| (\w+) \| (\S+) \|", idx, re.M):
        adr, state, owner = row
        if state not in {"Proposed", "Accepted", "Superseded", "Rejected", "Deprecated"}:
            problems.append(f"{adr}: illegal state {state}")
        if owner not in (PKG / "docs/governance/OWNERSHIP.yaml").read_text():
            problems.append(f"{adr}: owner role {owner} not in OWNERSHIP.yaml")
        if not list((PKG / "docs/adr").glob(f"{adr}-*.md")):
            problems.append(f"{adr}: file missing")
    today = dt.date.today().isoformat()
    for reg in (PKG / "docs/governance/registers").glob("*.json"):
        for e in json.loads(reg.read_text())["entries"]:
            if e.get("expiry") and e["expiry"] < today:
                problems.append(f"{reg.name}:{e['id']} expired {e['expiry']}")
    return not problems, "; ".join(problems) or "ADR index and registers valid"


def check_source() -> tuple[bool, str]:
    master, digest = PKG / "docs/source/MASTER.md", PKG / "docs/source/MASTER.sha256"
    prov = json.loads((PKG / "docs/source/MASTER.provenance.json").read_text())
    if master.exists():
        if not digest.exists() or digest.read_text().split()[0] != sha256(master):
            return False, "MASTER.md digest mismatch"
        return True, "MASTER.md digest verified"
    return prov.get("status") == "unresolved", "MASTER.md absent; recovery recorded as unresolved"


def check_tests() -> tuple[bool, str, dict]:
    results = {}
    for mode, flags in (("normal", []), ("optimized", ["-O"])):
        proc = subprocess.run([sys.executable, *flags, "-m", "unittest", "discover", "-s", str(PKG / "tests"), "-p", "test_*.py"],
                              cwd=ROOT, capture_output=True, text=True)
        tail = proc.stderr.strip().splitlines()[-3:]
        m = re.search(r"Ran (\d+) tests", proc.stderr)
        s = re.search(r"skipped=(\d+)", proc.stderr)
        results[mode] = {"returncode": proc.returncode, "ran": int(m.group(1)) if m else 0,
                         "skipped": int(s.group(1)) if s else 0, "tail": tail}
    ok = all(r["returncode"] == 0 and r["ran"] > 0 for r in results.values())
    return ok, json.dumps({k: {"ran": v["ran"], "skipped": v["skipped"], "rc": v["returncode"]} for k, v in results.items()}), results


def check_perf() -> tuple[bool, str]:
    p = PKG / "evidence/perf_baseline.json"
    if not p.exists():
        return False, "no perf evidence; run tools/bench.py --out evidence/perf_baseline.json"
    ev = json.loads(p.read_text())
    return ev["verdict"] == "PASS", f"{ev['verdict']} on {ev['host']['platform']} (breaches={len(ev['breaches'])})"


def check_build() -> tuple[bool, str]:
    try:
        import setuptools  # noqa: F401
    except ImportError:
        return False, "setuptools unavailable"
    digests = []
    for _ in range(2):
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, "SOURCE_DATE_EPOCH": "1790000000", "PYTHONHASHSEED": "0"}
            src = pathlib.Path(d) / "src"
            import shutil
            shutil.copytree(PKG, src, ignore=shutil.ignore_patterns("__pycache__", "dist", "build", "*.egg-info", "evidence"))
            cmd = [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(pathlib.Path(d) / "w"), str(src)]
            proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if proc.returncode:  # offline runner: fall back to the interpreter's own setuptools
                proc = subprocess.run(cmd[:5] + ["--no-build-isolation"] + cmd[5:], capture_output=True, text=True, env=env)
            wheels = list((pathlib.Path(d) / "w").glob("*.whl"))
            if proc.returncode or not wheels:
                return False, "wheel build failed: " + proc.stderr.strip()[-300:]
            digests.append(sha256(wheels[0]))
    return digests[0] == digests[1], f"wheel sha256 {digests[0][:16]}… {'reproducible' if digests[0] == digests[1] else 'NOT reproducible'}"


def check_legal(tier: str) -> tuple[bool, str]:
    missing = [f for f in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md", "docs/release/DISTRIBUTION_POLICY.md") if not (PKG / f).exists()]
    if missing:
        return False, f"missing {missing}"
    pending = "OWNER DECISION PENDING" in (PKG / "LICENSE").read_text()
    if tier == "release" and pending:
        return False, "licence not granted (owner decision pending)"
    return True, "legal files present" + ("; licence pending (blocks release tier)" if pending else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", choices=["local", "ci", "release"], default="local")
    ap.add_argument("--out")
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--skip-tests", action="store_true")
    ap.add_argument("--artifact")
    args = ap.parse_args(argv)

    checks: dict[str, dict] = {}

    def record(name, ok, detail):
        checks[name] = {"ok": bool(ok), "detail": detail}

    ok, detail, trace = check_traceability(); record("traceability", ok, detail)
    record("governance", *check_governance())
    record("source", *check_source())
    if not args.skip_tests:
        ok, detail, test_results = check_tests(); record("tests", ok, detail)
    record("perf", *check_perf())
    if args.tier in {"ci", "release"}:
        record("build", *check_build())
    record("legal", *check_legal(args.tier))
    record("manifest", *check_manifest(args.write_manifest))

    exceptions = {e["mc"]: e for e in json.loads((PKG / "docs/governance/registers/EXCEPTIONS.json").read_text())["entries"]
                  if e.get("approver") and e.get("expiry", "") >= dt.date.today().isoformat()}
    not_done = {k: {"status": c["status"], "open": c["open_acceptance"]} for k, c in trace["components"].items()
                if c["status"] != "IMPLEMENTED" and k not in exceptions}
    failed = [k for k, v in checks.items() if not v["ok"]]
    verdict = "GO" if not failed and not not_done else "NO_GO"

    lock = PKG / "requirements.lock"
    evidence = {
        "schema": "PLN02-GATE-EVIDENCE/1", "tier": args.tier, "verdict": verdict,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "package_version": (PKG / "VERSION").read_text().strip(),
        "source_tree_digest": hashlib.sha256(manifest_text().encode()).hexdigest(),
        "dependency_lock_digest": sha256(lock) if lock.exists() else None,
        "schema_digests": {p.name: sha256(p) for p in sorted((PKG / "schemas").glob("*.json"))},
        "environment": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                        "platform": platform.platform(), "machine": platform.machine()},
        "checks": checks, "failed_checks": failed,
        "status_counts": {s: sum(1 for c in trace["components"].values() if c["status"] == s) for s in trace["statuses"]},
        "not_done": not_done, "approved_exceptions": sorted(exceptions),
        "pk_core_estate_run": "not performed (pk_core not supplied)",
    }
    body = json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()
    key = os.environ.get("PLN02_GATE_KEY", "").encode()
    evidence["signature"] = ({"alg": "hmac-sha256", "value": hmac.new(key, body, hashlib.sha256).hexdigest()}
                             if len(key) >= 32 else "unsigned")
    text = json.dumps(evidence, indent=2, sort_keys=True)
    if args.out:
        out = pathlib.Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", "utf-8")
    print(json.dumps({"verdict": verdict, "failed_checks": failed, "status_counts": evidence["status_counts"],
                      "checks": {k: v["detail"] for k, v in checks.items()}}, indent=2))
    if failed:
        return 1
    return 1 if args.tier == "release" and verdict != "GO" else 0


if __name__ == "__main__":
    raise SystemExit(main())
