"""M30 - CycloneDX 1.5 SBOM + SHA256SUMS for the package tree. Deterministic:
same tree -> same bytes (no timestamps unless --timestamp is given).

    python tools/sbom.py --out evidence/sbom.cdx.json --sums SHA256SUMS
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, sys
from importlib import metadata

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {"__pycache__", ".git", "evidence"}


def files():
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and not SKIP & set(p.relative_to(ROOT).parts) and p.name != "SHA256SUMS":
            yield p


def dist(name):
    try:
        d = metadata.distribution(name)
        return {"version": d.version, "license": d.metadata.get("License-Expression") or d.metadata.get("License") or "UNKNOWN"}
    except metadata.PackageNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sums", required=True)
    ap.add_argument("--timestamp")
    a = ap.parse_args()
    sums, comps = [], []
    for p in files():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rel = p.relative_to(ROOT).as_posix()
        sums.append(f"{h}  {rel}")
        comps.append({"type": "file", "name": rel, "hashes": [{"alg": "SHA-256", "content": h}]})
    deps = []
    for name in ("cryptography", "cffi"):
        info = dist(name)
        deps.append({"type": "library", "name": name, "purl": f"pkg:pypi/{name}@{info['version']}" if info else None,
                     "version": info["version"] if info else "UNRESOLVED",
                     "licenses": [{"license": {"name": info["license"]}}] if info else [],
                     "properties": [{"name": "inv61:hash-status", "value": "NOT_RECORDED (index unreachable at build)"}]})
    deps.append({"type": "library", "name": "pk_core", "version": "UNRESOLVED",
                 "properties": [{"name": "inv61:status", "value": "BLOCKED - canonical source unknown, absent from archive"}]})
    version = (ROOT / "VERSION").read_text().strip()
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
           "metadata": {"component": {"type": "library", "name": "inv61-distributed-wit-rpc", "version": version}},
           "components": deps + comps}
    if a.timestamp:
        bom["metadata"]["timestamp"] = a.timestamp
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(bom, indent=1, sort_keys=True) + "\n")
    pathlib.Path(a.sums).write_text("\n".join(sums) + "\n")
    print(f"{len(comps)} files, {len(deps)} dependencies -> {a.out}, {a.sums}")


if __name__ == "__main__":
    sys.exit(main())
