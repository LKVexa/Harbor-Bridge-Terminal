"""Inventory and integrity for the ship and its berths (same conventions as
the DF containers: SHA256SUMS.txt binds every delivered file except itself;
MANIFEST.json's inventory excludes MANIFEST.json, SHA256SUMS.txt and the
build/run artefact directories)."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
from . import safety as SAFE
from . import Refusal
from typing import Dict, Iterable, List, Tuple

INVENTORY_EXCLUSIONS = ("__pycache__", "*.pyc", "_engines", "_studio", "_runs", "_scratch",
                        ".build", ".conformance.json", ".DS_Store", "Thumbs.db")
EXCLUSION_REASON = ("_engines/ (the hold's containers extracted and built), _studio/ (the hull's install "
                    "root), _runs/ (VERIFY/RUN records), _scratch/, .build/ and Python bytecode caches are "
                    "machine-specific artefacts produced by BUILD/VERIFY/RUN, not delivered content; a berth's "
                    "live fabric images (berths/<b>/<SLOT>/_fabric/, berths/<b>/_fabric/) are state, kept outside "
                    "every seal exactly as the studio keeps a container's fabric outside its container. "
                    "MANIFEST.json and SHA256SUMS.txt are excluded from their own inventory.")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


#: a berth's live fabric images (UC-2.0.0) live outside every seal, exactly as the studio keeps
#: a container's fabric outside its container: `berths/<b>/<SLOT>/_fabric/` and `berths/<b>/_fabric/`
#: (ship-relative), i.e. `<SLOT>/_fabric/` and `_fabric/` (berth-relative). Only those positions
#: are state; a cargo directory that happens to be called `_fabric` stays sealed.
FABRIC_STATE_DIR = "_fabric"
_SLOTS = ("DF_Small", "DF_Medium", "DF_Large", "DF_Xtra_Large", "DF_Fabric")


def is_fabric_state(rel: str) -> bool:
    parts = rel.split("/")
    for i, part in enumerate(parts):
        if part != FABRIC_STATE_DIR:
            continue
        if i == 0 or (i == 1 and parts[0] in _SLOTS):
            return True                                   # berth-relative
        if parts[0] == "berths" and (i == 2 or (i == 3 and parts[2] in _SLOTS)):
            return True                                   # ship-relative
    return False


def is_excluded(rel: str, exclusions: Iterable[str] = INVENTORY_EXCLUSIONS) -> bool:
    for part in rel.split("/"):
        for pat in exclusions:
            if fnmatch.fnmatch(part, pat):
                return True
    return is_fabric_state(rel)


def walk(root: str, exclude_top: Iterable[str] = ("MANIFEST.json", "SHA256SUMS.txt"),
         exclusions: Iterable[str] = INVENTORY_EXCLUSIONS) -> List[str]:
    out: List[str] = []
    for dp, dns, fns in os.walk(root):
        reld = os.path.relpath(dp, root).replace(os.sep, "/")
        reld = "" if reld == "." else reld + "/"
        dns[:] = sorted(d for d in dns if not is_excluded(reld + d, exclusions))
        for d in dns:
            SAFE.reject_link(os.path.join(dp, d))
        for fn in sorted(fns):
            rel = os.path.relpath(os.path.join(dp, fn), root).replace(os.sep, "/")
            if is_excluded(rel, exclusions) or rel in exclude_top:
                continue
            resolved = SAFE.contained_path(root, rel)
            if not os.path.isfile(resolved):
                raise Refusal("non-regular inventory file", {"path": rel})
            out.append(rel)
    return sorted(out)


def inventory(root: str) -> List[Dict[str, object]]:
    return [{"path": rel, "bytes": os.path.getsize(os.path.join(root, rel)),
             "sha256": sha256_file(os.path.join(root, rel))} for rel in walk(root)]


def write_sums(root: str, name: str = "SHA256SUMS.txt", extra: Iterable[str] = ("MANIFEST.json",)) -> str:
    rels = walk(root, exclude_top=(name, *[e for e in ("MANIFEST.json", "SHA256SUMS.txt") if e != name and e not in extra]))
    for e in extra:
        if os.path.isfile(os.path.join(root, e)) and e not in rels:
            rels.append(e)
    rels = sorted(set(rels) - {name})
    text = "\n".join(f"{sha256_file(os.path.join(root, r))}  {r}" for r in rels) + "\n"
    SAFE.atomic_write(SAFE.contained_path(root, name), text)
    return sha256_bytes(text.encode("utf-8"))


def reseal(root: str, reason: str, berths: Iterable[Dict[str, object]] = ()) -> Dict[str, object]:
    """Re-seal a sealed ship whose delivered content legitimately changed (a berth was loaded
    or unloaded here): MANIFEST.json's inventory is rebuilt from disk and SHA256SUMS.txt is
    rewritten. The assembly seal is kept (`assembly_seal`) and every re-seal is appended to
    `seal_lineage` with the digests it replaced, so a re-sealed ship says so; nothing is
    appended silently. Returns the lineage entry written."""
    import datetime as _dt
    from . import strictjson as _json
    mp = os.path.join(root, "MANIFEST.json")
    sp = os.path.join(root, "SHA256SUMS.txt")
    if not os.path.isfile(mp):
        raise FileNotFoundError("MANIFEST.json: the ship is not sealed; nothing to re-seal")
    with open(mp, encoding="utf-8") as fh:
        man = _json.load(fh)
    prev = {"manifest_sha256": sha256_file(mp), "sums_sha256": sha256_file(sp) if os.path.isfile(sp) else None,
            "file_count": man.get("file_count"), "total_bytes": man.get("total_bytes")}
    if "assembly_seal" not in man:
        man["assembly_seal"] = {"assembled_at_utc": man.get("assembled_at_utc"), **prev,
                                "note": "the seal the assembly host delivered; U0.1/U0.2 check the CURRENT seal (below)"}
    inv = inventory(root)
    man["files"] = inv
    man["file_count"] = len(inv)
    man["total_bytes"] = sum(int(f["bytes"]) for f in inv)
    blist = list(berths)
    man["berths"] = [{"berth": b["berth"], "kind": b.get("kind"), "scripts": b.get("scripts"), "sums_sha256": b.get("sums_sha256")} for b in blist]
    from . import UC_RELEASE
    man["uc_release"] = UC_RELEASE
    entry = {"utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "reason": reason,
             "replaced": prev, "file_count": len(inv), "total_bytes": man["total_bytes"]}
    man.setdefault("seal_lineage", []).append(entry)
    man["sealed_utc"] = entry["utc"]
    SAFE.atomic_json(mp, man)
    entry["sums_sha256"] = write_sums(root)
    return entry


def check_sums(root: str, name: str = "SHA256SUMS.txt") -> Dict[str, object]:
    path = SAFE.contained_path(root, name)
    ok, bad, missing, bound, errors = 0, [], [], set(), []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.rstrip("\r\n")
            if not line:
                continue
            if not re.fullmatch(r"[0-9a-fA-F]{64}  .+", line):
                errors.append(f"line {lineno}: malformed checksum record")
                continue
            digest, rel = line[:64].lower(), line[66:]
            try:
                p = SAFE.contained_path(root, rel)
            except Refusal as exc:
                errors.append(f"line {lineno}: {exc}")
                continue
            if rel in bound:
                errors.append(f"line {lineno}: duplicate path {rel}")
                continue
            bound.add(rel)
            if not os.path.isfile(p):
                missing.append(rel)
            elif sha256_file(p) == digest:
                ok += 1
            else:
                bad.append(rel)
    try:
        unbound = [r for r in walk(root, exclude_top=(name,)) if r not in bound]
    except Refusal as exc:
        unbound = []
        errors.append(str(exc))
    return {"ok": ok, "bad": bad, "missing": missing, "unbound": unbound, "errors": errors,
            "pass": not bad and not missing and not unbound and not errors}


def check_manifest_inventory(root: str, manifest: Dict[str, object]) -> Dict[str, object]:
    files, errors = {}, []
    for index, f in enumerate(manifest.get("files", [])):
        if not isinstance(f, dict) or not isinstance(f.get("path"), str):
            errors.append(f"record {index}: invalid file record")
            continue
        rel = f["path"]
        try:
            SAFE.contained_path(root, rel)
        except Refusal as exc:
            errors.append(f"record {index}: {exc}")
            continue
        if rel in files:
            errors.append(f"duplicate manifest path: {rel}")
        if type(f.get("bytes")) is not int or f["bytes"] < 0 or not re.fullmatch(r"[0-9a-f]{64}", str(f.get("sha256", ""))):
            errors.append(f"record {index}: invalid size or digest")
        files[rel] = f
    try:
        on_disk = walk(root)
    except Refusal as exc:
        on_disk = []
        errors.append(str(exc))
    mismatched = [rel for rel, f in files.items()
                  if not os.path.isfile(os.path.join(root, rel))
                  or os.path.getsize(os.path.join(root, rel)) != f.get("bytes")
                  or sha256_file(os.path.join(root, rel)) != f.get("sha256")]
    extra = [r for r in on_disk if r not in files]
    total_bytes = sum(f["bytes"] for f in files.values() if type(f.get("bytes")) is int)
    if manifest.get("total_bytes") != total_bytes:
        errors.append("total_bytes does not equal the inventory total")
    return {"inventoried": len(files), "on_disk": len(on_disk), "mismatched_or_missing": mismatched,
            "extra": extra, "errors": errors,
            "pass": not mismatched and not extra and not errors and manifest.get("file_count") == len(files)}


def dir_digest(root: str, skip: Iterable[str] = ("__pycache__",)) -> Tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in skip)
        for d in dns:
            SAFE.reject_link(os.path.join(dp, d))
        for fn in sorted(fns):
            if fn.endswith(".pyc") or fn in skip:
                # `skip` names directories AND files to leave out (a pinned digest file
                # excludes itself from the digest it states)
                continue
            p = os.path.join(dp, fn)
            SAFE.reject_link(p)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            h.update(f"{sha256_file(p)}  {rel}\n".encode("utf-8"))
            n += 1
    return h.hexdigest(), n
