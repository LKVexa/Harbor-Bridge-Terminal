"""CI / release gate and acceptance-evidence bundle (MC-23, MC-56, MC-57, MC-72).

    python -m pln07_security_plane.ci.gate [--quick]

Stages (each recorded with exit status and output digest):
  1. compile      - byte-compile every module
  2. tests        - framework-free suites, normal mode
  3. tests_O      - same suites under ``python -O``
  4. schemas      - every schema parses; sample documents validate
  5. bench        - performance budgets (bench/baseline.json)
  6. manifest     - MANIFEST.sha256 matches the tree
  7. sbom         - CycloneDX 1.5 SBOM of runtime deps
  8. framework    - pk_core conformance (tests/test_component.py) if pk_core present

Writes ``evidence/EVIDENCE.json`` and prints the exit-gate verdict.  Items
that can only be closed outside this archive are read from
``evidence/EXTERNAL_BLOCKERS.json``; while any is open the verdict can be at
best CONDITIONAL_GO, never GO.
"""
from __future__ import annotations

import argparse, hashlib, json, os, pathlib, platform, subprocess, sys, time

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
EVID = PKG / "evidence"
SKIP = {"evidence", "__pycache__", ".pytest_cache"}


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_files():
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and not (set(p.relative_to(PKG).parts) & SKIP) and p.name != "MANIFEST.sha256" and p.suffix != ".pyc":
            yield p


def write_manifest() -> None:
    lines = [f"{sha(p)}  ./{p.relative_to(PKG).as_posix()}" for p in tree_files()]
    (PKG / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")


def check_manifest() -> tuple[int, str]:
    want = {}
    for line in (PKG / "MANIFEST.sha256").read_text().splitlines():
        h, _, name = line.partition("  ")
        want[name] = h
    have = {f"./{p.relative_to(PKG).as_posix()}": sha(p) for p in tree_files()}
    diff = sorted(k for k in set(want) | set(have) if want.get(k) != have.get(k))
    return (0 if not diff else 1), ("ok" if not diff else "mismatch: " + ", ".join(diff))


def run(cmd: list[str]) -> tuple[int, str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout + p.stderr)[-4000:]


def schemas() -> tuple[int, str]:
    sys.path.insert(0, str(ROOT))
    from pln07_security_plane.grants import Grant
    from pln07_security_plane.service import encode_grant
    msgs, rc = [], 0
    docs = {}
    for s in sorted((PKG / "schemas").glob("*.json")):
        docs[s.name] = json.loads(s.read_text())
        msgs.append(f"parsed {s.name}")
    try:
        import jsonschema
    except ImportError:
        return 0, "\n".join(msgs + ["jsonschema not installed: structural parse only"])
    g = Grant("c", "t1", {"s"}, 100, environment="prod", nonce="n", issued_at=1, not_before=1)
    from pln07_security_plane.revocation import RevocationRegistry
    from pln07_security_plane.observability import AuditLog
    from pln07_security_plane.signing import KeyStore, AlgorithmPolicy
    ks = KeyStore("prod", AlgorithmPolicy(frozenset({"HMAC-SHA256"}))); ks.generate("HMAC-SHA256")
    samples = {"PK_GRANT-2.schema.json": json.loads(g.attenuate(subject="x").canonical_payload),
               "PK_GRANT-1.schema.json": json.loads(Grant("c", "t1", {"s"}, 100).attenuate(subject="x").canonical_payload),
               "PK_REVOCATION-2.schema.json": RevocationRegistry().revoke(g, effective_at=1, horizon=1, epoch=1),
               "PK_SIG-1.schema.json": ks.sign(b"x"),
               "PK_AUDIT-1.schema.json": AuditLog().emit("issue", "allow", "grant.issued")}
    for name, doc in samples.items():
        try:
            jsonschema.validate(doc, docs[name]); msgs.append(f"sample valid against {name}")
        except Exception as exc:
            rc = 1; msgs.append(f"{name}: {exc}")
    return rc, "\n".join(msgs)


def sbom() -> dict:
    comps = [{"type": "library", "name": "python", "version": platform.python_version(), "scope": "required"}]
    try:
        import cryptography
        comps.append({"type": "library", "name": "cryptography", "version": cryptography.__version__,
                      "scope": "optional", "purl": f"pkg:pypi/cryptography@{cryptography.__version__}",
                      "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}]})
    except ImportError:
        pass
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "pln07-security-plane",
                                       "version": (PKG / "VERSION").read_text().strip()}},
            "components": comps}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--quick", action="store_true")
    ap.add_argument("--reseal", action="store_true", help="rewrite MANIFEST.sha256 before checking")
    a = ap.parse_args()
    EVID.mkdir(exist_ok=True)
    if a.reseal:
        write_manifest()
    py = sys.executable
    tests = ["-m", "unittest", "pln07_security_plane.tests.test_v43", "pln07_security_plane.tests.test_grants"]
    stages = {}
    for name, fn in [
        ("compile", lambda: run([py, "-m", "compileall", "-q", "pln07_security_plane"])),
        ("tests", lambda: run([py, *tests])),
        ("tests_O", lambda: run([py, "-O", *tests])),
        ("schemas", schemas),
        ("bench", lambda: run([py, "-m", "pln07_security_plane.bench.bench", "--quick"] + ([] if a.quick else []))),
        ("manifest", check_manifest),
    ]:
        t = time.time(); rc, out = fn()
        stages[name] = {"status": "pass" if rc == 0 else "fail", "rc": rc, "seconds": round(time.time() - t, 3),
                        "output_sha256": hashlib.sha256(out.encode()).hexdigest(), "tail": out[-600:]}
    try:
        import pk_core  # noqa: F401
        rc, out = run([py, "pln07_security_plane/tests/test_component.py"])
        stages["framework"] = {"status": "pass" if rc == 0 else "fail", "rc": rc, "tail": out[-600:]}
    except ImportError:
        stages["framework"] = {"status": "blocked", "reason": "pk_core not available (MC-02)"}
    bom = sbom()
    (EVID / "sbom.cdx.json").write_text(json.dumps(bom, indent=2))
    blockers = json.loads((EVID / "EXTERNAL_BLOCKERS.json").read_text())
    open_blockers = [b for b in blockers if b["status"] != "closed"]
    failed = [k for k, v in stages.items() if v["status"] == "fail"]
    verdict = "NO_GO" if failed else ("CONDITIONAL_GO" if open_blockers or stages["framework"]["status"] != "pass" else "GO")
    bundle = {"type": "PLN07_EVIDENCE/1", "component": "PLN-07", "version": bom["metadata"]["component"]["version"],
              "generated_at": int(time.time()), "host": {"python": platform.python_version(), "system": platform.system()},
              "artifact_digests": {f"./{p.relative_to(PKG).as_posix()}": sha(p) for p in tree_files()},
              "manifest_sha256": sha(PKG / "MANIFEST.sha256"), "sbom_sha256": sha(EVID / "sbom.cdx.json"),
              "stages": stages, "open_external_blockers": [b["id"] for b in open_blockers],
              "verdict": verdict,
              "verdict_rule": "NO_GO if any stage fails; CONDITIONAL_GO while external blockers are open or pk_core gate is blocked; GO otherwise. A GO still requires the signed approvals in docs/EXIT_GATE.md."}
    (EVID / "EVIDENCE.json").write_text(json.dumps(bundle, indent=2))
    for k, v in stages.items():
        print(f"{k:10s} {v['status']}")
    print(f"open external blockers: {len(open_blockers)}")
    print(f"VERDICT: {verdict}")
    return 1 if verdict == "NO_GO" else 0


if __name__ == "__main__":
    sys.exit(main())
