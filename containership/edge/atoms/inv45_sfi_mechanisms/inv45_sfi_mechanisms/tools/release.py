"""Release evidence, SBOM, provenance, manifest and the production exit gate (A5, C090, C099, C100).

    python tools/release.py build [--bench RESULT.json]   # writes release/*.json
    python tools/release.py verify                        # recompute MANIFEST digests (deployment check)
    python tools/release.py gate                          # evaluate the C100 exit gate (exit 0 only on GO)

Signing: the organisation's approved signing mechanism is not available here.  ``build`` therefore signs
the manifest with an **ephemeral, non-production Ed25519 key** so the verification procedure itself is
exercised, and marks the signature ``"trust": "NONPRODUCTION-EPHEMERAL"``.  The exit gate refuses that
signature for production.
"""
from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "tools"))

import ci  # noqa: E402
import perf_gate  # noqa: E402

REL = ROOT / "release"
VERSION = (ROOT / "VERSION").read_text().strip()


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _files() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT).as_posix()
        if p.is_file() and not set(p.relative_to(ROOT).parts) & ci.EXCLUDE_DIRS and rel not in ci.EXCLUDE_FILES:
            out.append(p)
    return out


def manifest() -> dict:
    digest, n = ci.tree_digest()
    return {"schema": "PK_SFI_RELEASE_MANIFEST/1", "component": "inv45_sfi_mechanisms", "version": VERSION,
            "source_tree_sha256": digest, "files": [
                {"path": p.relative_to(ROOT).as_posix(), "sha256": _sha(p), "bytes": p.stat().st_size}
                for p in _files()],
            "schemas": sorted(p.name for p in (ROOT / "schemas").glob("*.schema.json")),
            "profile": "PK-SFI-WASM32-MVP-1",
            "config_defaults_sha256": __import__("inv45_sfi_mechanisms.production.config",
                                                 fromlist=["x"]).digest(
                __import__("inv45_sfi_mechanisms.production.config", fromlist=["x"]).validate(
                    dict(__import__("inv45_sfi_mechanisms.production.config", fromlist=["x"]).DEFAULTS)))}


def sbom() -> dict:
    def comp(name, version, purl, lic, scope="required", note=None):
        c = {"type": "library", "name": name, "version": version, "purl": purl, "scope": scope,
             "licenses": [{"expression": lic}] if lic else []}
        if note:
            c["properties"] = [{"name": "inv45:note", "value": note}]
        return c
    import importlib.metadata as md

    def ver(pkg):
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return "absent"
    node = ci.subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip() or "absent"
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "library", "name": "inv45-sfi-mechanisms", "version": VERSION,
                                       "licenses": [], "properties": [{"name": "inv45:license",
                                                                       "value": "NOT SELECTED (LICENSE-STATUS.md)"}]}},
            "components": [
                comp("cryptography", ver("cryptography"), f"pkg:pypi/cryptography@{ver('cryptography')}",
                     "Apache-2.0 OR BSD-3-Clause"),
                comp("node", node.lstrip("v"), f"pkg:generic/nodejs@{node.lstrip('v')}", "MIT",
                     note="V8 engine for the node-v8 execution adapter (external, not bundled)"),
                comp("jsonschema", ver("jsonschema"), f"pkg:pypi/jsonschema@{ver('jsonschema')}", "MIT",
                     scope="optional", note="test/contract lane only"),
                comp("pk_core", "UNRESOLVED", "pkg:generic/pk_core", None, scope="optional",
                     note="external checklist framework; version/digest not published (W-07)"),
                comp("python", platform.python_version(), f"pkg:generic/cpython@{platform.python_version()}",
                     "PSF-2.0", note="runtime; >=3.10 supported")]}


def check_waivers() -> dict:
    data = json.loads((REL / "waivers.json").read_text())
    today = _dt.date.today().isoformat()
    rows = []
    for w in data["waivers"]:
        effective = bool(w.get("approver")) and w.get("expires", "") >= today
        rows.append({"id": w["id"], "items": w["items"], "effective": effective,
                     "reason": "ok" if effective else ("no approver" if not w.get("approver") else "expired")})
    return {"effective": sum(r["effective"] for r in rows), "pending": sum(not r["effective"] for r in rows),
            "rows": rows}


def exit_gate(evidence: dict) -> dict:
    """C100: GO only if every production-readiness condition holds on this exact tree."""
    reasons = []
    ci_rep = evidence.get("ci", {})
    if ci_rep.get("overall") != "PASS":
        reasons.append(f"CI overall {ci_rep.get('overall')} (lanes not PASS: "
                       + ", ".join(k for k, v in ci_rep.get("lanes", {}).items() if v["status"] != "PASS") + ")")
    if ci_rep.get("source_tree_sha256") != evidence["manifest_source_tree_sha256"]:
        reasons.append("CI report was produced for a different source tree digest")
    pg = evidence.get("perf_gate") or {}
    if pg.get("overall") != "PASS":
        reasons.append(f"perf gate {pg.get('overall', 'NOT_RUN')}")
    reg = json.loads((ROOT / "requirements/requirements.json").read_text())
    open_items = [r["id"][-4:] for r in reg["requirements"] if r["status"] not in ("implemented",)]
    if open_items:
        reasons.append(f"{len(open_items)} checklist items not certified implemented (owner review/approval missing)")
    w = check_waivers()
    if w["pending"]:
        reasons.append(f"{w['pending']} waivers pending approval")
    own = (ROOT / "OWNERSHIP.md").read_text()
    if "UNASSIGNED" in own:
        reasons.append("accountable owners / release approver not bound (OWNERSHIP.md)")
    if evidence.get("signature", {}).get("trust") != "PRODUCTION":
        reasons.append("release manifest not signed with the organisation's production key")
    if evidence.get("pk_core") != "present":
        reasons.append("pk_core 100-item gate not run")
    return {"schema": "PK_SFI_EXIT_GATE/1", "version": VERSION, "decision": "NO_GO" if reasons else "GO",
            "reasons": reasons}


def build(bench: str | None) -> int:
    REL.mkdir(exist_ok=True)
    man = manifest()
    (REL / "sbom.cdx.json").write_text(json.dumps(sbom(), indent=1) + "\n")
    man_bytes = json.dumps(man, indent=1, sort_keys=True).encode() + b"\n"
    (REL / "MANIFEST.json").write_bytes(man_bytes)
    from inv45_sfi_mechanisms.production import trust
    key, pub = trust.new_ed25519()
    sig = base64.b64encode(key.sign(man_bytes)).decode()
    ci_path = REL / "ci_report.json"
    ci_rep = json.loads(ci_path.read_text()) if ci_path.exists() else {"overall": "NOT_RUN"}
    pg = None
    if bench:
        th = json.loads((ROOT / "benchmarks/thresholds.json").read_text())
        base = ROOT / th["regression"]["baseline"]
        pg = perf_gate.evaluate(json.loads(Path(bench).read_text()), th,
                                json.loads(base.read_text()) if base.exists() else None)
        (REL / "perf_gate.json").write_text(json.dumps(pg, indent=1) + "\n")
    import importlib.util
    evidence = {"schema": "PK_SFI_RELEASE_EVIDENCE/1", "version": VERSION,
                "manifest_sha256": hashlib.sha256(man_bytes).hexdigest(),
                "manifest_source_tree_sha256": man["source_tree_sha256"],
                "sbom_sha256": _sha(REL / "sbom.cdx.json"),
                "config_defaults_sha256": man["config_defaults_sha256"],
                "environment": {"python": platform.python_version(), "platform": platform.platform()},
                "pk_core": "present" if importlib.util.find_spec("pk_core") else "absent",
                "ci": ci_rep, "perf_gate": pg,
                "rtm": {"errors": __import__("rtm").check()},
                "waivers": check_waivers(),
                "signature": {"alg": "Ed25519", "over": "release/MANIFEST.json", "sig": sig, "public_key": pub,
                              "trust": "NONPRODUCTION-EPHEMERAL"}}
    gate = exit_gate(evidence)
    evidence["exit_gate"] = gate
    (REL / "evidence.json").write_text(json.dumps(evidence, indent=1, sort_keys=True) + "\n")
    (REL / "exit_gate.json").write_text(json.dumps(gate, indent=1) + "\n")
    prov = {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": "release/MANIFEST.json", "digest": {"sha256": evidence["manifest_sha256"]}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv45/tools-release@1",
                                              "externalParameters": {"version": VERSION},
                                              "resolvedDependencies": [
                                                  {"name": "source-tree", "digest": {"sha256": man["source_tree_sha256"]}},
                                                  {"name": "sbom", "digest": {"sha256": evidence["sbom_sha256"]}}]},
                          "runDetails": {"builder": {"id": "local:tools/release.py (not a hardened builder)"},
                                         "metadata": {"invocationId": "unsigned-local-build"}}},
            "signature_trust": "NONPRODUCTION-EPHEMERAL"}
    (REL / "provenance.json").write_text(json.dumps(prov, indent=1) + "\n")
    print(json.dumps({"exit_gate": gate["decision"], "reasons": gate["reasons"]}, indent=1))
    return 0


def verify() -> int:
    man = json.loads((REL / "MANIFEST.json").read_text())
    bad = [f["path"] for f in man["files"] if not (ROOT / f["path"]).exists() or _sha(ROOT / f["path"]) != f["sha256"]]
    ev = json.loads((REL / "evidence.json").read_text())
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(ev["signature"]["public_key"])).verify(
            base64.b64decode(ev["signature"]["sig"]), (REL / "MANIFEST.json").read_bytes())
        sig_ok = True
    except Exception:
        sig_ok = False
    print(json.dumps({"files": len(man["files"]), "mismatched": bad, "signature_valid": sig_ok,
                      "signature_trust": ev["signature"]["trust"]}, indent=1))
    return 0 if not bad and sig_ok else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        bench = sys.argv[sys.argv.index("--bench") + 1] if "--bench" in sys.argv else None
        return build(bench)
    if cmd == "verify":
        return verify()
    if cmd == "gate":
        ev = json.loads((REL / "evidence.json").read_text())
        g = exit_gate(ev)
        print(json.dumps(g, indent=1))
        return 0 if g["decision"] == "GO" else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
