"""Release manifest/checksums, SBOM and verification (items 64, 66, 68).

    python -m inv67_kubernetes_integration_mechanism.governance.release build
    python -m inv67_kubernetes_integration_mechanism.governance.release verify [--key-env INV67_RELEASE_KEY]

The manifest lists every shipped file (sorted, POSIX paths, size, sha256) and
is deterministic: no timestamps, platform-independent ordering. Verification
fails on unexpected, missing or altered files and on version mismatch. When a
key is provided via environment the manifest is HMAC-sealed; otherwise it is
explicitly marked ``unsigned`` (never implied signed).
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = "RELEASE_MANIFEST.json"
EXCLUDE_DIRS = {"__pycache__", ".git", ".mypy_cache", ".ruff_cache", "perf"}
EXCLUDE_FILES = {MANIFEST}
EXCLUDE_PREFIX = ("evidence/components/", "evidence/GATE_RESULT.json", "evidence/ACCEPTANCE_BUNDLE.json",
                  "evidence/TRACEABILITY.json", "evidence/test_results.json")


def version(root=ROOT) -> str:
    return (root / "VERSION").read_text().strip()


def shipped(root=ROOT) -> list[pathlib.Path]:
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in EXCLUDE_DIRS)
        for f in sorted(fns):
            p = pathlib.Path(dp) / f
            rel = p.relative_to(root).as_posix()
            if f in EXCLUDE_FILES or f.endswith((".pyc", ".pyo")) or rel.startswith(EXCLUDE_PREFIX):
                continue
            out.append(p)
    return sorted(out, key=lambda p: p.relative_to(root).as_posix())


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def build(root=ROOT, key: bytes | None = None) -> dict:
    files = [{"path": p.relative_to(root).as_posix(), "size": p.stat().st_size, "sha256": sha256(p)} for p in shipped(root)]
    body = {"schema": "INV67_RELEASE_MANIFEST/1", "component": "INV-67", "version": version(root), "files": files}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    body["manifest_sha256"] = digest
    body["seal"] = ({"alg": "HMAC-SHA256", "mac": hmac.new(key, digest.encode(), hashlib.sha256).hexdigest()}
                    if key else {"alg": "unsigned", "note": "no release key in this environment; tamper-evident only"})
    return body


def verify(root=ROOT, manifest: dict | None = None, key: bytes | None = None) -> list[str]:
    m = manifest or json.loads((root / MANIFEST).read_text())
    problems = []
    body = {k: m[k] for k in ("schema", "component", "version", "files")}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != m.get("manifest_sha256"):
        problems.append("manifest digest mismatch (manifest edited)")
    if key is not None:
        mac = m.get("seal", {}).get("mac", "")
        if not hmac.compare_digest(mac, hmac.new(key, digest.encode(), hashlib.sha256).hexdigest()):
            problems.append("manifest seal does not verify")
    if m["version"] != version(root):
        problems.append(f"version mismatch: manifest {m['version']} vs VERSION {version(root)}")
    want = {f["path"]: f for f in m["files"]}
    have = {p.relative_to(root).as_posix(): p for p in shipped(root)}
    for rel in sorted(set(want) - set(have)):
        problems.append(f"missing: {rel}")
    for rel in sorted(set(have) - set(want)):
        problems.append(f"unexpected: {rel}")
    for rel in sorted(set(want) & set(have)):
        if sha256(have[rel]) != want[rel]["sha256"]:
            problems.append(f"altered: {rel}")
    return problems


def sbom(root=ROOT) -> dict:
    """CycloneDX 1.5 SBOM. Runtime dependencies: none (stdlib only)."""
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {
                "type": "library", "name": "inv67-kubernetes-integration-mechanism", "version": version(root),
                "licenses": [{"license": {"name": "UNDECLARED (see EXC-010)"}}]}},
            "components": [],
            "dependencies": [{"ref": "inv67-kubernetes-integration-mechanism", "dependsOn": []}],
            "properties": [{"name": "inv67:runtime-deps", "value": "python-stdlib-only"},
                           {"name": "inv67:dev-deps",
                            "value": "optional: pyyaml (manifest parse test), ruff, mypy, bandit (CI only)"}]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "verify", "sbom"])
    ap.add_argument("--key-env", default="INV67_RELEASE_KEY")
    a = ap.parse_args(argv)
    key = os.environ.get(a.key_env, "").encode() or None
    if a.cmd == "sbom":
        (ROOT / "sbom.cdx.json").write_text(json.dumps(sbom(), indent=2) + "\n")
        print("sbom.cdx.json written")
        return 0
    if a.cmd == "build":
        m = build(key=key)
        (ROOT / MANIFEST).write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
        print(f"{MANIFEST}: {len(m['files'])} files, sha256 {m['manifest_sha256']}, seal {m['seal']['alg']}")
        return 0
    probs = verify(key=key)
    print("OK" if not probs else "\n".join(probs))
    return 0 if not probs else 1


if __name__ == "__main__":
    sys.exit(main())
