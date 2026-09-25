"""The hull face of a berth: its BERTH.pal witness as a PA Language Studio
container, built, sealed and expected to answer R2 == reference witness -- and,
since UC-2.0.0, a container with its own .tif fabric.

This is where the two scaffolds meet. The studio's runtime is the BOTTLE ROCKET
4.7.0 VM (the ship's Large engine); the berth's `studio/main.lctlc` is the
LCTLC/1.2 field lowering of BERTH.pal's row-sequence witness (the witness in R2,
then the tick cell of storage object 0 advanced and the witness mirrored into
cell 8); `studio new --from` wraps it in a sealed container in the studio's own
registry; `studio build` compiles and (where OpenSSL exists) signs it; `studio
run` executes it on the RAM-backed device fabric and compares R2 with the
declared expectation; `studio fabric init` gives the container its own .tif
(`_studio/state/berth_<b>.fabric.tif`) and `studio fabric tick` executes the
picture; and `studio test` keeps every berth honest afterwards -- a berth whose
cargo manifest changed changes BERTH.pal, its witness, and therefore its answer.
"""

from __future__ import annotations

from . import strictjson as json
import os
from typing import Any, Dict, Optional

from . import ShipError, Refusal
from . import engines as E
from .berth import berth_dir


def container_name(berth: str) -> str:
    from . import face_container_name
    return face_container_name(berth)


def _expected(berth: str) -> Dict[str, Any]:
    p = os.path.join(berth_dir(berth), "BERTH_SEAL.json")
    if not os.path.isfile(p):
        raise Refusal(f"berth {berth!r} has no BERTH_SEAL.json", {"berth": berth})
    return json.load(open(p, encoding="utf-8"))


def register(berth: str, rebuild: bool = True) -> Dict[str, Any]:
    """Create (or refresh) the berth's studio container from studio/main.lctlc,
    build it, capture its expectation and check R2 against the seal."""
    s = E.studio()
    if not s.installed:
        raise Refusal("the hull is not installed at _studio/; run BUILD first", {"root": E.studio_root()})
    src = os.path.join(berth_dir(berth), "studio", "main.lctlc")
    if not os.path.isfile(src):
        raise Refusal(f"berth {berth!r} has no studio face", {"expected": src})
    exp = _expected(berth)
    cname = container_name(berth)
    existing = {c.get("name"): c for c in (s.list_containers().get("containers") or [])}
    out: Dict[str, Any] = {"berth": berth, "container": cname, "expected_R2": exp["reference_witness"]}
    if cname in existing:
        if rebuild:
            s.remove_container(cname)
            out["replaced"] = True
        else:
            out["existing"] = True
    from . import host as H
    can_run, why = H.hull_execution()
    if cname not in existing or rebuild:
        n = s.new_app(cname, source=src, version="1.0.0")
        out["path"] = n["path"]
        b = s.build_app(cname)
        out["build"] = {"ok": b.get("ok"), "state": b.get("state"), "image_bytes": b.get("image_bytes") or b.get("bytes")}
        if can_run:
            cap = s.capture_expectations(cname, registers=["R2"])
            out["captured_expect"] = (cap.get("expect") or {}).get("registers")
    if can_run:
        r = s.run_app(cname)
        out["run"] = {"ok": r.get("ok"), "status_name": r.get("status_name"), "trap": r.get("trap"),
                      "R2": (r.get("registers") or {}).get("R2"), "execution_mode": r.get("execution_mode"),
                      "expectations_met": r.get("expectations_met")}
        out["r2_equals_reference"] = ((r.get("registers") or {}).get("R2") == exp["reference_witness"])
        out["ok"] = bool(r.get("ok")) and out["r2_equals_reference"]
    else:
        # a compile-only hull: the face is built and sealed, its picture is made, but it cannot be run here --
        # no expectation is captured (that would be written by hand, not observed) and no R2 is claimed
        out["run"] = {"ok": None, "skipped": why}
        out["r2_equals_reference"] = None
        out["host_limited"] = why
        out["ok"] = bool((out.get("build") or {}).get("ok", True))
    try:
        man = s.app_manifest(s.resolve_app(cname))
        out["state"] = man.get("state")
        out["image_sha256"] = (man.get("image") or {}).get("sha256") or man.get("image_sha256")
    except Exception:  # noqa: BLE001
        pass
    # the container's own .tif fabric (kept across re-registrations; `uc fabric init --force` resets it)
    out["fabric"] = _ensure_fabric(s, cname, force=False, berth=berth)
    return out


def _ensure_fabric(s, cname: str, force: bool = False, berth: Optional[str] = None) -> Dict[str, Any]:
    if not hasattr(s, "fabric_init"):
        return {"created": False, "reason": "the hull has no fabric images (needs PA Language Studio 2.0.0)"}
    try:
        tif = s.fabric_path(cname)
        if os.path.isfile(tif) and not force:
            return {"created": False, "kept": True, "path": tif}
        if os.path.isfile(tif):
            os.remove(tif)
        if berth and not force:
            from . import tif_fabric as TF
            mirror = TF.mirror_path(berth, None)
            if os.path.isfile(mirror):
                os.makedirs(os.path.dirname(tif), exist_ok=True)
                import shutil as _sh
                _sh.copyfile(mirror, tif)
                return {"created": False, "restored_from_mirror": mirror, "path": tif}
        r = s.fabric_init(cname, from_state=False)
        return {"created": True, "path": r.get("fabric"), "grid": r.get("grid"), "bytes": r.get("bytes")}
    except Exception as exc:  # noqa: BLE001
        return {"created": False, "error": f"{type(exc).__name__}: {exc}",
                "reason": "Pillow (PIL) is required for the .tif fabric" if "PIL" in str(exc) or "Pillow" in str(exc) else None}


def check(berth: str) -> Dict[str, Any]:
    """Run the berth's studio container against its expectation (no rebuild)."""
    s = E.studio()
    if not s.installed:
        return {"skipped": "hull not installed at _studio/"}
    exp = _expected(berth)
    cname = container_name(berth)
    names = {c.get("name") for c in (s.list_containers().get("containers") or [])}
    if cname not in names:
        return {"skipped": f"no studio container {cname} (run BUILD or `uc studio-register {berth}`)"}
    from . import host as H
    can_run, why = H.hull_execution()
    if not can_run:
        return {"skipped": why, "host_limited": True, "container": cname, "expected_R2": exp["reference_witness"]}
    r = s.run_app(cname)
    v = s.verify_app(cname)
    return {"berth": berth, "container": cname, "ok": bool(r.get("ok")) and (r.get("registers") or {}).get("R2") == exp["reference_witness"],
            "status_name": r.get("status_name"), "trap": r.get("trap"), "R2": (r.get("registers") or {}).get("R2"),
            "expected_R2": exp["reference_witness"], "execution_mode": r.get("execution_mode"),
            "expectations_met": r.get("expectations_met"), "verify": {k: v.get(k) for k in ("ok", "state", "sealed", "seal_ok", "gate") if k in v}}


def test_all() -> Dict[str, Any]:
    s = E.studio()
    if not s.installed:
        return {"skipped": "hull not installed"}
    from . import host as H
    can_run, why = H.hull_execution()
    if not can_run:
        return {"skipped": why, "host_limited": True,
                "containers": [c.get("name") for c in (s.list_containers().get("containers") or [])]}
    return s.test_all()
