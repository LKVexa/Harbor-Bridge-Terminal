"""Hull cargo: a berth whose cargo is itself a sealed studio container gets a seat in the hull.

The ship breaks a project up script by script and sorts every script into a node
(the berth). When the project *is* a PA21 Language Studio container -- a `CONTAINER.json`
(`PA21C/1`) and its `RELEASE_CONTENTS.sha256` at some prefix of the source, with the
files the seal lists -- the berth is still that container, only broken up: every file
is in the slot the policy chose, byte-identical, under its original relative path. So
the ship can put it back together (exactly the files the seal lists, from the slots
the sort ledger names) and **mount** it in the hull: `studio import` (which re-verifies
the seal), the container's own key trusted because loading the berth is the operator's
decision and BERTH.json records the key's digest, and -- if the cargo carries a fabric
picture (`*.fabric.tif` under the same prefix) -- that picture installed as the
container's own `.tif` in the studio (`_studio/state/<name>.fabric.tif`). From then on
`studio fabric tick <name>` executes the container's own program on its own picture,
`uc run <berth>` ticks it along with the berth's six pictures, and the picture is
mirrored into the berth's state dir (`berths/<b>/_fabric/<name>.fabric.tif`, or a short
`mnt_<sha8>` name where that would not fit the delivered-path budget) so the
running state travels with the ship and BUILD restores it on another machine.

The ship does not interpret what the mounted program does with its picture; that is the
container's own business (a mesh-driven cell, for instance, waits for its mesh).
"""

from __future__ import annotations

import datetime as _dt
from . import strictjson as json
import os
import shutil
import tempfile
from typing import Any, Dict, List, Optional

from . import UC_RELEASE, NODE_IDS, NODE_CONTAINER, ShipError, Refusal
from . import engines as E
from . import safety as SAFE
from . import ucmanifest as M

MOUNTS_SCHEMA = "UC/HULL_MOUNTS/1"
CONTAINER_MANIFEST = "CONTAINER.json"
CONTAINER_SEAL = "RELEASE_CONTENTS.sha256"
CONTAINER_FORMAT = "PA21C/1"


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _berth_dir(berth: str) -> str:
    from .berth import berth_dir
    return berth_dir(berth)


def _ledger(berth: str) -> Dict[str, Any]:
    p = os.path.join(_berth_dir(berth), "SORT_LEDGER.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _cargo_path(berth: str, rec: Dict[str, Any], root: Optional[str] = None) -> str:
    return SAFE.contained_path(root or _berth_dir(berth), NODE_CONTAINER[rec["node"]] + "/cargo/" + (rec.get("stored_as") or rec["path"]))


# --------------------------------------------------------------------------
# detection (from the sort ledger alone)
# --------------------------------------------------------------------------

def detect(berth: str, ledger: Optional[Dict[str, Any]] = None, root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every studio container carried in the berth's cargo: prefix, name, the files the seal lists
    (each with the slot it was sorted to), the pubkey and the picture, if any."""
    ledger = ledger or _ledger(berth)
    recs = {r["path"]: r for r in ledger["records"]}
    out: List[Dict[str, Any]] = []
    for path, rec in sorted(recs.items()):
        if path != CONTAINER_MANIFEST and not path.endswith("/" + CONTAINER_MANIFEST):
            continue
        prefix = path[: -len(CONTAINER_MANIFEST)]
        seal_rec = recs.get(prefix + CONTAINER_SEAL)
        if not seal_rec:
            continue
        try:
            with open(_cargo_path(berth, rec, root), encoding="utf-8") as fh:
                man = json.load(fh)
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(man, dict) or man.get("format") != CONTAINER_FORMAT or not man.get("name"):
            continue
        listed = []
        try:
            with open(_cargo_path(berth, seal_rec, root), encoding="utf-8") as fh:
                for line in fh:
                    line = line.rstrip("\n")
                    if not line.strip() or "  " not in line:
                        continue
                    digest, rel = line.split("  ", 1)
                    listed.append({"path": rel, "sha256": digest})
        except Exception:  # noqa: BLE001
            continue
        files = []
        complete = True
        for it in listed:
            r = recs.get(prefix + it["path"])
            if r is None:
                complete = False
                files.append({"path": it["path"], "present": False})
            else:
                files.append({"path": it["path"], "present": True, "node": r["node"], "slot": NODE_CONTAINER[r["node"]],
                              "sha256_matches_seal": r["sha256"] == it["sha256"], "rule": r["rule"]})
        pictures = [p for p in recs if p.startswith(prefix) and p.endswith(".fabric.tif")]
        pref = [p for p in pictures if man["name"] in os.path.basename(p)]
        picture = (pref or pictures or [None])[0]
        pubkey = recs.get(prefix + str(man.get("image", "")).rsplit(".", 1)[0] + ".pubkey") if man.get("image") else None
        out.append({"prefix": prefix, "name": str(man["name"]), "version": man.get("version"), "format": man.get("format"),
                    "entry": man.get("entry"), "image": man.get("image"), "state": (man.get("fabric") or {}).get("state"),
                    "devices": (man.get("fabric") or {}).get("devices"), "built_by": man.get("built_by"),
                    "digests": man.get("digests"), "files": files, "listed": len(listed),
                    "complete": complete and all(f.get("sha256_matches_seal") for f in files if f.get("present")),
                    "picture": picture, "picture_node": recs[picture]["node"] if picture else None,
                    "pubkey": pubkey["path"] if pubkey else None, "pubkey_sha256": pubkey["sha256"] if pubkey else None,
                    "manifest_path": path, "seal_path": prefix + CONTAINER_SEAL})
    return out


# --------------------------------------------------------------------------
# reassembly and mounting
# --------------------------------------------------------------------------

def reassemble(berth: str, mount: Dict[str, Any], dest: str) -> Dict[str, Any]:
    """Copy exactly the files the container's seal lists (plus the seal) from the slots the sort
    ledger names into `dest`, under their original relative paths."""
    ledger = _ledger(berth)
    recs = {r["path"]: r for r in ledger["records"]}
    os.makedirs(dest, exist_ok=True)
    copied = 0
    for f in mount["files"]:
        if not f.get("present"):
            raise ShipError("the container is incomplete in the berth", {"missing": f["path"], "container": mount["name"]})
        src = _cargo_path(berth, recs[mount["prefix"] + f["path"]])
        dst = SAFE.contained_path(dest, f["path"])
        if M.sha256_file(src) != recs[mount["prefix"] + f["path"]]["sha256"]:
            raise Refusal("cargo changed since its sort ledger was sealed", {"path": f["path"]})
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        copied += 1
    seal_src = _cargo_path(berth, recs[mount["seal_path"]])
    shutil.copyfile(seal_src, os.path.join(dest, CONTAINER_SEAL))
    return {"dest": dest, "files": copied + 1}


def registry_path() -> str:
    return os.path.join(E.studio_root(), "uc_mounts.json")


def read_registry() -> Dict[str, Any]:
    p = registry_path()
    if os.path.isfile(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError) as exc:
            raise Refusal("mount registry cannot be read; refusing to discard ownership state", {"path": p, "error": str(exc)}) from exc
    return {"schema": MOUNTS_SCHEMA, "uc_release": UC_RELEASE, "mounts": {}}


def write_registry(reg: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(registry_path()), exist_ok=True)
    reg["written_utc"] = utcnow()
    SAFE.atomic_json(registry_path(), reg)


def mounts_of(berth: str) -> List[str]:
    reg = read_registry()
    return sorted(n for n, m in reg["mounts"].items() if m.get("berth") == berth)


def _mirror_dir(berth: str) -> str:
    from .tif_fabric import berth_state_dir
    return berth_state_dir(berth)


def mount(berth: str, *, force: bool = False, trust: bool = True, restore_state: bool = True) -> Dict[str, Any]:
    """Mount every studio container the berth carries into the hull. Idempotent."""
    s = E.studio()
    if not s.installed:
        raise Refusal("the hull is not installed at _studio/; run BUILD first", {"root": E.studio_root()})
    found = detect(berth)
    reg = read_registry()
    out: Dict[str, Any] = {"berth": berth, "mounts": [], "found": len(found)}
    existing = {c.get("name"): c for c in (s.list_containers().get("containers") or [])}
    for mnt in found:
        name = SAFE.validate_name(mnt["name"])
        rec: Dict[str, Any] = {"container": name, "prefix": mnt["prefix"], "files": mnt["listed"], "complete": mnt["complete"]}
        if not mnt["complete"]:
            rec.update({"mounted": False, "reason": "the container is incomplete in the berth (a listed file is missing or differs from its seal)"})
            out["mounts"].append(rec)
            continue
        owner = (reg["mounts"].get(name) or {}).get("berth")
        if owner != berth and name in existing:
            rec.update({"mounted": False, "reason": f"a container named {name!r} is already mounted by berth {owner!r}"})
            out["mounts"].append(rec)
            continue
        if name in existing and owner == berth and not force:
            rec.update({"mounted": True, "already": True, "path": existing[name].get("path")})
        else:
            tmp = tempfile.mkdtemp(prefix="uc-mount-")
            try:
                reassemble(berth, mnt, tmp)
                r = s.import_container(tmp, force=True)
                rec.update({"mounted": True, "already": False, "path": r.get("path"), "seal": {k: r["seal"].get(k) for k in ("sealed", "checked", "listed")},
                            "gate": (r.get("gate") or {}).get("satisfied") if isinstance(r.get("gate"), dict) else r.get("gate"),
                            "state": r.get("state"), "devices": r.get("devices")})
            except Exception as exc:  # noqa: BLE001
                rec.update({"mounted": False, "reason": f"{type(exc).__name__}: {exc}"})
                out["mounts"].append(rec)
                continue
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        # trust the container's own key: the operator loaded the berth; BERTH.json records the key digest
        if trust and mnt.get("pubkey"):
            try:
                t = s.trust(name)
                rec["trusted_key"] = {"ok": bool(t.get("ok")), "key": t.get("key"), "pubkey_sha256": mnt.get("pubkey_sha256")}
            except Exception as exc:  # noqa: BLE001
                rec["trusted_key"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        # the container's own picture: the mirror (running state) first, else the cargo's genesis picture
        pic = s.fabric_path(name)
        from . import tif_fabric as TF
        mirror = TF.mirror_path(berth, name)
        rec["picture"] = {"path": pic}
        if os.path.isfile(pic) and not force:
            rec["picture"].update({"kept": True})
        elif restore_state and os.path.isfile(mirror):
            os.makedirs(os.path.dirname(pic), exist_ok=True)
            shutil.copyfile(mirror, pic)
            rec["picture"].update({"restored_from_mirror": mirror})
        elif mnt.get("picture"):
            ledger = _ledger(berth)
            recs = {r["path"]: r for r in ledger["records"]}
            src = _cargo_path(berth, recs[mnt["picture"]])
            os.makedirs(os.path.dirname(pic), exist_ok=True)
            shutil.copyfile(src, pic)
            rec["picture"].update({"installed_from_cargo": mnt["picture"], "sha256": M.sha256_file(src)})
        else:
            rec["picture"].update({"none": True, "note": "the cargo carries no *.fabric.tif; `studio fabric init` would make an empty one"})
        reg["mounts"][name] = {"berth": berth, "prefix": mnt["prefix"], "mounted_utc": utcnow(), "picture_from": mnt.get("picture"),
                               "pubkey_sha256": mnt.get("pubkey_sha256"), "version": mnt.get("version")}
        out["mounts"].append(rec)
    write_registry(reg)
    out["ok"] = all(m.get("mounted") for m in out["mounts"]) if out["mounts"] else True
    return out


def unmount(berth: str) -> Dict[str, Any]:
    reg = read_registry()
    names = [n for n, m in reg["mounts"].items() if m.get("berth") == berth]
    out: Dict[str, Any] = {"berth": berth, "unmounted": [], "errors": []}
    try:
        s = E.studio()
    except Exception as exc:  # noqa: BLE001
        return {"berth": berth, "unmounted": [], "errors": [f"{type(exc).__name__}: {exc}"]}
    for n in names:
        try:
            if s.installed:
                have = {c.get("name") for c in (s.list_containers().get("containers") or [])}
                if n in have:
                    s.remove_container(n)
                sd = s.state_dir()
                if os.path.isdir(sd):
                    for fn in os.listdir(sd):
                        if fn == f"{n}.state" or fn.startswith(f"{n}.fabric."):
                            os.remove(os.path.join(sd, fn))
            out["unmounted"].append(n)
        except Exception as exc:  # noqa: BLE001
            out["errors"].append(f"{n}: {type(exc).__name__}: {exc}")
        reg["mounts"].pop(n, None)
    write_registry(reg)
    return out


def tick_mounts(berth: str, *, view: bool = True) -> Dict[str, Any]:
    """`studio fabric tick` for every container mounted from this berth; mirror the picture."""
    out: Dict[str, Any] = {}
    names = mounts_of(berth)
    if not names:
        return out
    s = E.studio()
    if not s.installed:
        return {n: {"ticked": False, "reason": "hull not installed"} for n in names}
    have = {c.get("name") for c in (s.list_containers().get("containers") or [])}
    from . import host as H
    can_run, why = H.hull_execution()
    for n in names:
        if n not in have:
            out[n] = {"ticked": False, "reason": "not mounted in the hull (run BUILD)"}
            continue
        if not can_run:
            out[n] = {"ticked": False, "reason": why, "host_limited": True, "path": s.fabric_path(n)}
            continue
        try:
            t = s.fabric_tick(n, view=view)
            rec = {"ticked": bool(t.get("ran")), "ok": bool(t.get("ok")), "tick": t.get("tick"), "pages": t.get("pages"),
                   "status_name": t.get("status_name"), "trap": t.get("trap"), "fabric_changed": t.get("fabric_changed"),
                   "monotonic": t.get("monotonic"), "path": t.get("fabric"), "reason": t.get("reason")}
            mirror_pictures(berth, [n])
            out[n] = rec
        except Exception as exc:  # noqa: BLE001
            out[n] = {"ticked": False, "error": f"{type(exc).__name__}: {exc}"}
    return out


def mirror_pictures(berth: str, names: Optional[List[str]] = None) -> Dict[str, str]:
    """Copy the mounted containers' pictures (and views) from the studio's state dir into the berth's
    state dir, so the running state travels with the ship."""
    s = E.studio()
    if not s.installed:
        return {}
    d = _mirror_dir(berth)
    os.makedirs(d, exist_ok=True)
    out = {}
    from . import tif_fabric as TF
    for n in (names or mounts_of(berth)):
        for suffix in (".fabric.tif", ".fabric.png"):
            src = os.path.join(s.state_dir(), n + suffix)
            if os.path.isfile(src):
                dst = os.path.join(d, TF.mirror_name(berth, n, suffix))
                shutil.copyfile(src, dst)
                out[n + suffix] = dst
    return out


def status(berth: str) -> Dict[str, Any]:
    reg = read_registry()
    names = mounts_of(berth)
    out: Dict[str, Any] = {"berth": berth, "detected": [m["name"] for m in detect(berth)], "mounted": {}}
    try:
        s = E.studio()
        have = {c.get("name") for c in (s.list_containers().get("containers") or [])} if s.installed else set()
    except Exception:  # noqa: BLE001
        have = set()
    for n in names:
        rec = dict(reg["mounts"].get(n) or {})
        rec["in_hull"] = n in have
        try:
            pic = s.fabric_path(n)
            rec["picture"] = pic
            rec["picture_present"] = os.path.isfile(pic)
            if rec["picture_present"]:
                fr = s.fabric_frames(n)
                rec["tick"] = (fr.get("frames") or [{}])[0].get("tick") if fr.get("frames") else None
                rec["pages"] = fr.get("pages")
        except Exception:  # noqa: BLE001
            pass
        out["mounted"][n] = rec
    return out
