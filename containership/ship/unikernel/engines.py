"""The hold and the hull, made runnable: engines and the studio.

* `extract_hold()`   unzips the five DF containers from hold/ into _engines/
                     (byte-identical; each container's own SHA256SUMS.txt is
                     re-checked after extraction) and pins their digests;
* `build_engines()`  runs each node container's own ./BUILD in place, so the
                     four VMs -- the ship's engines -- can be bound;
* `bind()`           imports the hold's `dfabric` package and `pacore` core
                     (one copy, from _engines/DF_Fabric) and returns the bound
                     engine roots; nothing in the ship duplicates that code;
* `install_studio()` installs the hull (PA21 Language Studio 1.3.0) into
                     _studio/ from the Large engine's VM package, bound to a
                     PA21 delivery root (the full delivery if given, else the
                     ledger excerpt in hold/PA21_LEDGER_EXCERPT).

_engines/ and _studio/ are BUILD outputs, excluded from the inventory.
"""

from __future__ import annotations

import importlib
from . import strictjson as json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from typing import Any, Dict, List, Optional

from . import ShipError, Refusal, NODE_IDS, NODE_CONTAINER, FABRIC_CONTAINER, SLOTS
from . import ucmanifest as M
from . import safety as SAFE

HERE = os.path.dirname(os.path.abspath(__file__))
SHIP = os.path.abspath(os.path.join(HERE, "..", ".."))


def ship_root() -> str:
    return SHIP


def hold_dir() -> str:
    return os.path.join(SHIP, "hold")


def hull_dir() -> str:
    return os.path.join(SHIP, "hull")


def engines_dir() -> str:
    return os.path.join(SHIP, "_engines")


def studio_root() -> str:
    return os.path.join(SHIP, "_studio")


def runs_dir() -> str:
    d = os.path.join(SHIP, "_runs")
    os.makedirs(d, exist_ok=True)
    return d


def hold_pins() -> Dict[str, Any]:
    p = os.path.join(hold_dir(), "HOLD_DIGEST.json")
    return json.load(open(p, encoding="utf-8")) if os.path.isfile(p) else {}


def _fs_case_insensitive(where: str) -> bool:
    """Does the filesystem at `where` fold case (NTFS/APFS by default)?"""
    import tempfile as _tf
    try:
        os.makedirs(where, exist_ok=True)
        d = _tf.mkdtemp(prefix=".case-", dir=where)
        try:
            with open(os.path.join(d, "A"), "w") as fh:
                fh.write("a")
            return os.path.exists(os.path.join(d, "a"))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    except OSError:
        return False


def _sh(cmd: List[str], cwd: str, timeout: int = 3600) -> Dict[str, Any]:
    from .supervisor import run
    return run(cmd, cwd=cwd, timeout=timeout)



# --------------------------------------------------------------------------
# hold -> engines
# --------------------------------------------------------------------------

def hold_state() -> Dict[str, Any]:
    """What the hold holds and whether it matches HOLD_DIGEST.json."""
    pins = hold_pins()
    out = {"hold": hold_dir(), "containers": {}, "pass": True}
    for slot in SLOTS:
        zp = os.path.join(hold_dir(), f"{slot}.zip")
        rec = {"zip": zp, "present": os.path.isfile(zp)}
        if rec["present"]:
            rec["sha256"] = M.sha256_file(zp)
            pinned = (pins.get("zips") or {}).get(f"{slot}.zip")
            rec["pinned"] = pinned
            rec["match"] = bool(pinned and pinned == rec["sha256"])
            if not rec["match"]:
                out["pass"] = False
        else:
            out["pass"] = False
        out["containers"][slot] = rec
    return out


def extract_hold(force: bool = False) -> Dict[str, Any]:
    """Extract every hold zip into _engines/<slot>/ (idempotent by digest)."""
    trust = hold_state()
    if not trust["pass"]:
        raise Refusal("hold archives are missing or do not match all five required pins", trust)
    SAFE.contained_path(ship_root(), "_engines")
    os.makedirs(engines_dir(), exist_ok=True)
    marker = os.path.join(engines_dir(), "EXTRACTED.json")
    prev = json.load(open(marker, encoding="utf-8")) if os.path.isfile(marker) else {}
    out: Dict[str, Any] = {"engines_dir": engines_dir(), "containers": {}}
    for slot in SLOTS:
        zp = os.path.join(hold_dir(), f"{slot}.zip")
        if not os.path.isfile(zp):
            raise ShipError(f"the hold has no {slot}.zip", {"hold": hold_dir()})
        digest = M.sha256_file(zp)
        dest = os.path.join(engines_dir(), slot)
        rec = {"zip_sha256": digest, "dir": dest, "extracted": False, "own_sums": None}
        if (not force and os.path.isdir(dest) and prev.get(slot, {}).get("zip_sha256") == digest
                and os.path.isfile(os.path.join(dest, "SHA256SUMS.txt"))):
            rec["extracted"] = "cached"
            prev_limits = prev.get(slot, {}).get("host_limits") or {}
        else:
            if os.path.isdir(dest):
                shutil.rmtree(dest)
            skipped: List[Dict[str, str]] = []
            collisions: List[str] = []
            with zipfile.ZipFile(zp) as z:
                SAFE.inspect_zip(z)
                names = z.namelist()
                top = sorted({n.split("/")[0] for n in names if n.strip()})
                if top != [slot]:
                    raise ShipError(f"{slot}.zip does not contain exactly the top-level directory {slot}/",
                                    {"top_level": top[:5]})
                # a container may carry paths this host cannot hold (a pair differing only by case on a
                # case-insensitive filesystem; a path over Windows' MAX_PATH): extract member by member,
                # record what the host refused, and judge the container's own sums with that in mind
                lower_seen: Dict[str, str] = {}
                for n in names:
                    lo = n.lower()
                    if lo in lower_seen and lower_seen[lo] != n:
                        collisions.append(n)
                    lower_seen.setdefault(lo, n)
                for zi in z.infolist():
                    try:
                        target_name = zi.filename.rstrip("/")
                        SAFE.contained_path(engines_dir(), target_name)
                        z.extract(zi, engines_dir())
                    except OSError as exc:
                        skipped.append({"name": zi.filename, "error": f"{type(exc).__name__}: {exc}"[:200]})
                for zi in z.infolist():
                    mode = (zi.external_attr >> 16) & 0o777
                    p = os.path.join(engines_dir(), zi.filename)
                    if mode and os.path.isfile(p):
                        try:
                            os.chmod(p, mode)
                        except OSError:
                            pass
            for launcher in ("BUILD", "VERIFY", "RUN"):
                p = os.path.join(dest, launcher)
                if os.path.isfile(p):
                    os.chmod(p, 0o755)
            rec["extracted"] = True
            rec["host_limits"] = {"skipped_by_host": skipped, "case_collisions_in_zip": collisions,
                                  "filesystem_case_insensitive": _fs_case_insensitive(engines_dir())}
            prev_limits = rec["host_limits"]
        chk = M.check_sums(dest)  # the DF container's own G0.1, re-derived here
        rec["own_sums"] = {"ok": chk["ok"], "bad": chk["bad"][:5], "missing": chk["missing"][:5], "pass": chk["pass"]}
        rec["host_limits"] = prev_limits
        if not chk["pass"]:
            # explained by the host?  every bad/missing/unbound file must be one the host refused, or one of a
            # case-colliding pair on a case-insensitive filesystem; anything else is a real failure
            top_prefix = slot + "/"
            refused = {x["name"][len(top_prefix):] for x in (prev_limits.get("skipped_by_host") or []) if x["name"].startswith(top_prefix)}
            colliding = {x[len(top_prefix):].lower() for x in (prev_limits.get("case_collisions_in_zip") or [])}
            fs_ci = bool(prev_limits.get("filesystem_case_insensitive"))
            unexplained = list(chk.get("errors", [])) + [f for f in chk["bad"] + chk["missing"] + chk["unbound"]
                           if not (f in refused or (fs_ci and f.lower() in colliding))]
            rec["own_sums"]["host_limited"] = not unexplained
            rec["own_sums"]["unexplained"] = unexplained[:5]
            if unexplained:
                raise ShipError(f"{slot} does not verify after extraction", rec["own_sums"])
        out["containers"][slot] = rec
    SAFE.atomic_json(marker, out["containers"])
    return out


def build_engines(force: bool = False) -> Dict[str, Any]:
    """Run each node container's own ./BUILD in _engines/ (the C VMs compile
    into vm/<pkg>/.build; the QVM has nothing to compile)."""
    from . import host as H
    out: Dict[str, Any] = {"nodes": {}, "host_limited": {}}
    for nid in NODE_IDS:
        cont = os.path.join(engines_dir(), NODE_CONTAINER[nid])
        if not os.path.isdir(cont):
            raise ShipError(f"engine {NODE_CONTAINER[nid]} is not extracted; run extract_hold() first",
                            {"dir": cont})
        r = _sh([sys.executable, "-B", os.path.join(cont, "adapter", "dfabric", "cli.py"), "node-build"], cont, timeout=1800)
        tail = "\n".join(r["stdout"].strip().splitlines()[-6:])
        rec = {"container": NODE_CONTAINER[nid], "returncode": r["returncode"], "seconds": r["seconds"], "tail": tail}
        # the container's own BUILD says "blocked: no C toolchain ..." (exit 3) where the host has none: a host limit,
        # not a failure of the engine -- recorded as such, with what would lift it
        blocked = None
        try:
            blocked = json.loads(r["stdout"]).get("blocked")
        except Exception:  # noqa: BLE001
            pass
        if r["returncode"] != 0 and (blocked or (not H.facts()["c_toolchain"] and nid != "N_XLARGE")):
            rec["host_limited"] = blocked or H.limits().get("no_c_toolchain")
            out["host_limited"][nid] = rec["host_limited"]
        out["nodes"][nid] = rec
    out["pass"] = all(v["returncode"] == 0 for v in out["nodes"].values())
    out["ok"] = all(v["returncode"] == 0 or v.get("host_limited") for v in out["nodes"].values())
    out["built"] = sorted(n for n, v in out["nodes"].items() if v["returncode"] == 0)
    return out


_BOUND: Dict[str, Any] = {}


def bind(require: bool = True) -> Dict[str, Any]:
    """Import the hold's dfabric + pacore and locate the bound engine roots."""
    if _BOUND.get("dfabric") is not None:
        return _BOUND
    fab = os.path.join(engines_dir(), FABRIC_CONTAINER)
    if not os.path.isdir(fab):
        if require:
            raise ShipError("the hold is not extracted; run BUILD (extract_hold) first", {"engines": engines_dir()})
        return {"dfabric": None, "roots": {}, "located": {}}
    for p in (os.path.join(fab, "adapter"), os.path.join(fab, "core", "reference")):
        if p not in sys.path:
            sys.path.insert(0, p)
    dfabric = importlib.import_module("dfabric")
    gates = importlib.import_module("dfabric.gates")
    fr = importlib.import_module("dfabric.fabric_runtime")
    nodes = importlib.import_module("dfabric.nodes")
    from . import host as H
    adapted = H.adapt_nodes(nodes)            # e.g. no `sh`: the N_XLARGE column verifier goes through java directly
    located = gates.locate_nodes(fab, engines_dir())
    roots = gates.bindable_roots(located)
    _BOUND.update({"dfabric": dfabric, "gates": gates, "fabric_runtime": fr,
                   "witness": importlib.import_module("dfabric.witness"),
                   "nodes": nodes,
                   "lang": importlib.import_module("pacore.lang"),
                   "fabric_container": fab, "located": located, "roots": roots, "host": adapted})
    return _BOUND


def engines_status() -> Dict[str, Any]:
    fab = os.path.join(engines_dir(), FABRIC_CONTAINER)
    if not os.path.isdir(fab):
        return {"extracted": False, "bound": {}, "reason": "hold not extracted (run BUILD)"}
    b = bind(require=False)
    return {"extracted": True,
            "bound": {n: (n in b["roots"]) for n in NODE_IDS},
            "roots": b["roots"],
            "located": {n: {"present": r["present"], "sums_match": r["sums_match"]} for n, r in b["located"].items()},
            "host": b.get("host")}


# --------------------------------------------------------------------------
# hull -> studio
# --------------------------------------------------------------------------

def hull_studio_module():
    if hull_dir() not in sys.path:
        sys.path.insert(0, hull_dir())
    return importlib.import_module("pa21studio")


def hull_version() -> str:
    try:
        return str(getattr(hull_studio_module(), "VERSION", getattr(hull_studio_module(), "__version__", "")))
    except Exception:  # pragma: no cover
        return ""


def large_vm_root() -> str:
    cont = os.path.join(engines_dir(), NODE_CONTAINER["N_LARGE"])
    vm = os.path.join(cont, "vm")
    if not os.path.isdir(vm):
        raise ShipError("the Large engine is not extracted", {"dir": cont})
    subs = [d for d in sorted(os.listdir(vm)) if os.path.isdir(os.path.join(vm, d))]
    if len(subs) != 1:
        raise ShipError("the Large engine's vm/ does not hold exactly one package", {"vm": vm, "found": subs})
    return os.path.join(vm, subs[0])


def default_pa21_root() -> str:
    return os.path.join(hold_dir(), "PA21_LEDGER_EXCERPT")


def studio(pa21_root: Optional[str] = None):
    """The hull's Studio bound to _studio/ (installed if needed)."""
    mod = hull_studio_module()
    s = mod.Studio(studio_root())
    return s


def install_studio(pa21_root: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
    mod = hull_studio_module()
    s = mod.Studio(studio_root())
    if s.installed and not force:
        st = s.status()
        return {"installed": True, "already": True, "root": studio_root(),
                "execution_mode": st.get("execution_mode"), "signing": (st.get("signing") or {}).get("available")}
    pa21 = pa21_root or default_pa21_root()
    t0 = time.perf_counter()
    r = s.install(vm_source=large_vm_root(), pa21_root=pa21, force=force)
    st = s.status()
    return {"installed": bool(st.get("installed")), "already": False, "root": studio_root(),
            "seconds": round(time.perf_counter() - t0, 2),
            "steps": [{"step": x["step"], "ok": x["ok"]} for x in r.get("steps", [])],
            "pa21_root": pa21, "execution_mode": st.get("execution_mode"),
            "signing": (st.get("signing") or {}).get("available")}


def studio_status() -> Dict[str, Any]:
    try:
        mod = hull_studio_module()
        s = mod.Studio(studio_root())
        if not s.installed:
            return {"installed": False, "root": studio_root()}
        st = s.status()
        return {"installed": True, "root": studio_root(), "execution_mode": st.get("execution_mode"),
                "signing": (st.get("signing") or {}).get("available"),
                "containers": [c.get("name") for c in (s.list_containers().get("containers") or [])]}
    except Exception as exc:  # noqa: BLE001
        return {"installed": False, "root": studio_root(), "error": f"{type(exc).__name__}: {exc}"}
