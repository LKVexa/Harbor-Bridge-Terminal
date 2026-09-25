#!/usr/bin/env python3
"""Install the supplied edge-component atoms into UC280/edge (one-shot assembly script, kept for provenance)."""
import hashlib, json, os, re, shutil, sys, zipfile
from pathlib import Path

SRC = Path("/mnt/user-data/uploads/Edge Components in")
SHIP = Path(sys.argv[1]).resolve()
EDGE = SHIP / "edge"

REQUESTED = [l.strip() for l in open(Path(__file__).with_name("UC280_EDGE_REQUESTED.txt")) if l.strip()]

# Where one element arrived as several *distinct* archives, the canonical build is named here, with the reason.
CANONICAL_OVERRIDE = {
    "INV-30": ("inv30_capability_hardware_sandbox_v4.3.0_1.zip",
               "4.3.0 full package (128 files, 111 tests pass; the byte-identical v4.3.0 copy is recorded as a duplicate); the 4.2.0_hardened(1) archive is a 15-file remediation-checklist overlay retained as a variant"),
    "INV-55": ("inv55_secrets_integration_v4.3.0_checklist_applied_1.zip",
               "checklist-applied build with an importable package name and a fully green suite; the plain v4.3.0 archive (package dir 'inv55_secrets_integration_v4.3.0', 3 failing tests) is retained as a variant"),
    "INV-61": ("inv61_distributed_wit_rpc_v4.3.0_1.zip",
               "_1 build has the larger green suite (122 pass / 0 fail); the other v4.3.0 archive fails mutual-TLS identity binding and is retained as a variant"),
    "INV-66": ("inv66_enterprise_wasm_control_plane_v4.3.0_1.zip",
               "_1 build (202 files, importable package name, 134 tests pass) supersedes the 114-file v4.3.0 archive, retained as a variant"),
}
EVIDENCE_ONLY = {"gap04_v4.3.0_release_evidence.zip": "GAP-04"}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def element_of(name):
    m = re.match(r"(gap|inv|pln|sch)(\d\d)_", name)
    if m:
        return f"{m.group(1).upper()}-{m.group(2)}"
    if name.startswith("iOS735_LCTL"):
        return "EXT-IOS735-LCTL"
    raise SystemExit(f"unrecognised atom {name}")


def version_of(name):
    m = re.search(r"v?(\d+\.\d+\.\d+(?:\.dev\d+)?(?:-candidate)?)", name)
    return m.group(1) if m else None


def key_of(name):
    base = name[:-4]
    base = re.sub(r"[-_]v?\d+\.\d+\.\d+.*$", "", base)
    return base.lower()


def safe_extract(zp, dest):
    with zipfile.ZipFile(zp) as z:
        for info in z.infolist():
            n = info.filename.replace("\\", "/")
            if n.startswith("/") or ".." in n.split("/") or re.match(r"^[A-Za-z]:", n):
                raise SystemExit(f"unsafe member {n} in {zp.name}")
            if "__pycache__" in n.split("/") or n.endswith((".pyc", ".pyo")):
                continue
            target = dest / n
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as s, open(target, "wb") as d:
                shutil.copyfileobj(s, d)


def main():
    if EDGE.exists():
        raise SystemExit("edge/ already present; refusing to overwrite")
    (EDGE / "source").mkdir(parents=True)
    records, by_hash = [], {}
    for name in REQUESTED:
        p = SRC / name
        h = sha(p)
        rec = {"archive": name, "sha256": h, "bytes": p.stat().st_size, "element": element_of(name),
               "declared_version": version_of(name)}
        if h in by_hash:
            rec["byte_identical_to"] = by_hash[h]
            rec["stored_as"] = f"source/{by_hash[h]}"
        else:
            by_hash[h] = name
            shutil.copy2(p, EDGE / "source" / name)
            rec["stored_as"] = f"source/{name}"
        records.append(rec)

    # choose one canonical archive per element among distinct archives
    elements = {}
    for r in records:
        if r["archive"] in EVIDENCE_ONLY or "byte_identical_to" in r:
            continue
        elements.setdefault(r["element"], []).append(r)
    atoms = []
    for el, rs in sorted(elements.items()):
        if len(rs) > 1:
            canon_name, why = CANONICAL_OVERRIDE[el]
        else:
            canon_name, why = rs[0]["archive"], "single distinct archive supplied"
        for r in rs:
            canonical = r["archive"] == canon_name
            r["role"] = "canonical" if canonical else "variant"
            r["selection_reason"] = why
            key = key_of(r["archive"]) if canonical else r["archive"][:-4]
            rel = f"atoms/{key}" if canonical else f"variants/{key}"
            safe_extract(SRC / r["archive"], EDGE / rel)
            r["installed_at"] = rel
            if canonical:
                atoms.append({"element": el, "key": key, "path": rel, "archive": r["archive"],
                              "sha256": r["sha256"], "declared_version": r["declared_version"]})
    for r in records:
        if r["archive"] in EVIDENCE_ONLY:
            el = EVIDENCE_ONLY[r["archive"]]
            atom = next(a for a in atoms if a["element"] == el)
            dest = f"{atom['path']}/_release_evidence"
            safe_extract(SRC / r["archive"], EDGE / dest)
            r["role"] = "release-evidence"; r["installed_at"] = dest
            atom["release_evidence"] = dest
        elif "byte_identical_to" in r:
            r["role"] = "duplicate"
            r["installed_at"] = next(x["installed_at"] for x in records if x["archive"] == r["byte_identical_to"])

    # locate each atom's package root and VERSION file
    for a in atoms:
        root = EDGE / a["path"]
        cands = sorted([p for p in root.rglob("pyproject.toml") if "tests" not in p.parts], key=lambda p: len(p.parts))
        pkg = cands[0].parent if cands else root
        a["package_root"] = str(pkg.relative_to(EDGE)).replace(os.sep, "/")
        vf = sorted(root.rglob("VERSION"), key=lambda p: len(p.parts))
        a["package_version"] = vf[0].read_text(errors="replace").strip()[:40] if vf else None
        tests = sorted([p for p in root.rglob("tests") if p.is_dir() and any(p.rglob("test*.py"))], key=lambda p: len(p.parts))
        a["tests"] = str(tests[0].relative_to(EDGE)).replace(os.sep, "/") if tests else None
        a["files"] = sum(1 for p in root.rglob("*") if p.is_file())

    manifest = {"schema": "UC/EDGE_ATOMS/1", "candidate": "UC-2.8.0",
                "source_folder": "Edge Components in", "requested_archives": len(records),
                "stored_unique_archives": len(by_hash), "byte_identical_duplicates": sum(1 for r in records if r.get("role") == "duplicate"),
                "elements": len(atoms), "variants": sum(1 for r in records if r.get("role") == "variant"),
                "archives": records, "atoms": atoms}
    (EDGE / "EDGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k not in ("archives", "atoms")}, indent=2))


if __name__ == "__main__":
    main()
