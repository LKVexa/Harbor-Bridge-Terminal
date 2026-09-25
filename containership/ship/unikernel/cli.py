"""`uc` -- the Unikernel Containership command surface (behind BUILD / VERIFY / RUN / LOAD).

  uc status                                  what the ship holds; engines, hull, berths
  uc build [--pa21 ROOT] [--no-studio]       extract + build the engines from the hold; install the hull; register berth studio faces
  uc load SOURCE --name NAME --kind vm|subsystem [--replace] [--note TEXT]
                                             break a project into scripts, sort each into a node, give it its own berth
  uc unload NAME
  uc berths                                  the bill of lading
  uc sort FILE [FILE...]                     explain where a script would go and why
  uc verify [NAME] [--quick] [--no-hull]     the ship battery (or one berth's battery)
  uc run NAME [--ticks N] [--interval S] [--profile P]
                                             one tick (or N) of the berth's .tif fabric: every container's picture read,
                                             executed on its engine (the hull face by the hull's VM), written back as a frame
  uc run NAME --sealed [--programs replica,pipeline,bsp] [--profile P] [--bundle BERTH|CARGO]
                                             the sealed bundles' programs on the four engines (replica, pipeline, BSP)
  uc fabric init|tick|live|status|view|frames NAME [--force] [--ticks N] [--interval S]
                                             the berth's six pictures: (re)materialise from genesis, tick, run in flux, look
  uc mount NAME [--force] [--no-trust]       hull cargo: re-assemble the studio container(s) the berth carries from its slots
                                             and mount them in the hull with their own pictures (BUILD does this too)
  uc mounts NAME                             what the berth has mounted in the hull, and the state of their pictures
  uc slot-run NAME SLOT CARGO_PATH           run one runnable cargo script on its engine
  uc studio-register NAME                    (re)build the berth's hull face container
  uc studio-test                             studio test over every berth container
  uc seal [--reason TEXT]                    re-seal the ship (MANIFEST.json inventory + SHA256SUMS.txt) after its
                                             delivered content changed; load/unload do this themselves (--no-reseal to skip)

Exit codes: 0 ok · 1 fail · 2 rejected · 3 blocked/refused.
"""

from __future__ import annotations

import argparse
import datetime as _dt
from . import strictjson as json
import os
import sys
from typing import Any, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
SHIP = os.path.abspath(os.path.join(HERE, "..", ".."))
if os.path.join(SHIP, "ship") not in sys.path:
    sys.path.insert(0, os.path.join(SHIP, "ship"))

from unikernel import UC_RELEASE, UC_NAME, NODE_IDS, NODE_CONTAINER, SLOTS, ShipError, Refusal  # noqa: E402
from unikernel import engines as E  # noqa: E402
from unikernel import berth as BT  # noqa: E402
from unikernel import registry as R  # noqa: E402
from unikernel import sorter  # noqa: E402
from unikernel import safety as SAFE

EXIT_OK, EXIT_FAIL, EXIT_REJECTED, EXIT_BLOCKED = 0, 1, 2, 3


def _utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _emit(obj: Any, code: int = EXIT_OK, out: Optional[str] = None) -> int:
    text = json.dumps(obj, indent=2, sort_keys=True, default=str)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        SAFE.atomic_write(out, text + "\n")
    print(text)
    return code


def _reseal(reason: str, enabled: bool = True) -> Optional[dict]:
    """Re-seal a sealed ship after load/unload so U0.1/U0.2 describe the ship as it now is
    (the assembly seal is kept in MANIFEST.json's `assembly_seal`; each re-seal is appended to
    `seal_lineage`). A ship that was never sealed (no MANIFEST.json) is left alone."""
    from unikernel import ucmanifest as M
    if not enabled or not os.path.isfile(os.path.join(SHIP, "MANIFEST.json")):
        return None
    return M.reseal(SHIP, reason, berths=R.scan()["berths"])


def cmd_seal(a) -> int:
    from unikernel import ucmanifest as M
    if not os.path.isfile(os.path.join(SHIP, "MANIFEST.json")):
        return _emit({"refused": True, "reason": "MANIFEST.json not present: the ship is not sealed (this is an assembly tree)"}, EXIT_BLOCKED)
    entry = M.reseal(SHIP, a.reason or "uc seal", berths=R.scan()["berths"])
    chk = M.check_sums(SHIP)
    return _emit({"schema": "UC/SEAL_RESULT/1", "resealed": entry, "sums_check": {"pass": chk["pass"], "ok": chk["ok"], "bad": chk["bad"], "missing": chk["missing"], "unbound": chk["unbound"]}},
                 EXIT_OK if chk["pass"] else EXIT_FAIL, out=a.out)


def cmd_status(a) -> int:
    from unikernel import host as H
    reg = R.scan()
    return _emit({"schema": "UC/STATUS/1", "ship": UC_NAME, "uc_release": UC_RELEASE, "root": SHIP, **H.record(),
                  "hold": E.hold_state(), "engines": E.engines_status(), "hull": E.studio_status(),
                  "berths": [{"berth": b["berth"], "kind": b["kind"], "scripts": b["scripts"],
                              "per_node": {n: b["per_node"].get(n, {}).get("count") for n in NODE_IDS}} for b in reg["berths"]]}, out=a.out)


def _err(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def cmd_build(a) -> int:
    """BUILD: extract + build the engines, install the hull, register every berth's face, materialise every
    container's picture, mount the hull cargo, rebuild the bill of lading -- each berth on its own, so one
    berth's trouble (or a host limit) never stops the rest; every step recorded in _runs/BUILD_<stamp>.json."""
    from unikernel import host as H
    stamp = _utc()
    out_json = a.out or os.path.join(E.runs_dir(), f"BUILD_{stamp}.json")
    rec: dict = {"schema": "UC/BUILD/1", "uc_release": UC_RELEASE, "executed_at_utc": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                 **H.record(), "problems": []}
    print(f"== UC BUILD {UC_NAME} -- {UC_RELEASE}", flush=True)
    for k, v in H.limits().items():
        print(f"  [HOST] {k}: {v}", flush=True)
    try:
        rec["extract"] = {k: {"extracted": v["extracted"], "own_sums_pass": v["own_sums"]["pass"], "host_limits": v.get("host_limits")}
                          for k, v in E.extract_hold(force=a.force)["containers"].items()}
        print(f"  [OK] hold extracted: {', '.join(sorted(rec['extract']))}", flush=True)
        rec["engines"] = E.build_engines()
        for nid, v in rec["engines"]["nodes"].items():
            print(f"  [{'OK' if v['returncode'] == 0 else 'HOST' if v.get('host_limited') else 'FAIL'}] engine {nid} ({v['container']})"
                  + (f": {v['host_limited']}" if v.get("host_limited") else ""), flush=True)
        for nid, v in rec["engines"]["nodes"].items():
            if v["returncode"] != 0 and not v.get("host_limited"):
                rec["problems"].append(f"engine {nid} did not build (exit {v['returncode']}): {v.get('tail', '')[-300:]}")
        rec["engines"]["host_adaptations"] = (E.bind(require=False).get("host") or {}).get("adaptations")
    except (ShipError, Refusal) as exc:
        rec["blocked"] = exc.as_dict()
        rec["verdict"] = "BLOCKED"
        return _emit(rec, EXIT_BLOCKED, out=out_json)
    if not a.no_studio:
        try:
            rec["hull"] = E.install_studio(pa21_root=a.pa21, force=a.force)
            print(f"  [OK] hull installed: execution {rec['hull'].get('execution_mode')}", flush=True)
        except Exception as exc:  # noqa: BLE001 -- the hull's own StudioError included
            rec["hull"] = {"installed": False, "error": _err(exc)}
            rec["problems"].append(f"hull install: {_err(exc)}")
            print(f"  [FAIL] hull install: {_err(exc)}", flush=True)
        can_run, why = H.hull_execution()
        rec["hull_can_execute"] = {"ok": can_run, "reason": why}
        if rec["hull"].get("installed") and not can_run:
            print(f"  [HOST] {why}", flush=True)
        if rec["hull"].get("installed"):
            from unikernel import studio_face
            rec["studio_faces"] = {}
            n_ok = 0
            for b in R.scan()["berths"]:
                try:
                    r = studio_face.register(b["berth"], rebuild=True)
                    rec["studio_faces"][b["berth"]] = r
                    n_ok += 1 if r.get("ok") else 0
                    if not r.get("ok"):
                        rec["problems"].append(f"studio face {b['berth']}: not ok ({r.get('run')})")
                except Exception as exc:  # noqa: BLE001 -- ShipError, Refusal, the hull's StudioError, anything: on to the next berth
                    rec["studio_faces"][b["berth"]] = {"ok": False, "error": _err(exc)}
                    rec["problems"].append(f"studio face {b['berth']}: {_err(exc)}")
            print(f"  [{'OK' if n_ok == len(rec['studio_faces']) else 'FAIL'}] studio faces: {n_ok}/{len(rec['studio_faces'])} built"
                  + ("" if can_run else " (compile-only hull: no expectation captured, no run)"), flush=True)
    # every container's own .tif fabric: the live images, from the sealed genesis (kept if present)
    from unikernel import tif_fabric as TF
    okf, whyf = TF.available()
    rec["fabric"] = {"available": okf, "reason": whyf or None, "berths": {}}
    if okf:
        n_ok = 0
        for b in R.scan()["berths"]:
            try:
                r = TF.init_live(b["berth"], force=a.force, face=not a.no_studio)
                rec["fabric"]["berths"][b["berth"]] = {k: (v.get("created") or v.get("kept") or v.get("reason")) for k, v in r["containers"].items()} | {
                    "hull_face": (r.get("hull_face") or {}).get("created") or (r.get("hull_face") or {}).get("kept") or bool((r.get("hull_face") or {}).get("restored_from_mirror")) or (r.get("hull_face") or {}).get("reason")}
                n_ok += 1
            except Exception as exc:  # noqa: BLE001
                rec["fabric"]["berths"][b["berth"]] = {"error": _err(exc)}
                rec["problems"].append(f"fabric images {b['berth']}: {_err(exc)}")
        print(f"  [{'OK' if n_ok == len(rec['fabric']['berths']) else 'FAIL'}] .tif fabric images: {n_ok}/{len(rec['fabric']['berths'])} berths", flush=True)
    else:
        print(f"  [SKIP] .tif fabric images: {whyf}", flush=True)
    # hull cargo: studio containers carried by berths, mounted in the hull with their pictures
    if not a.no_studio and rec.get("hull", {}).get("installed"):
        from unikernel import hullmount as HM
        rec["hull_mounts"] = {}
        n_m = n_ok = 0
        for b in R.scan()["berths"]:
            try:
                m = HM.mount(b["berth"], force=a.force)
                if m["found"]:
                    rec["hull_mounts"][b["berth"]] = {x["container"]: {"mounted": x.get("mounted"), "already": x.get("already"),
                                                                        "picture": {k: v for k, v in (x.get("picture") or {}).items() if k != "path"},
                                                                        "reason": x.get("reason")} for x in m["mounts"]}
                    n_m += len(m["mounts"])
                    n_ok += sum(1 for x in m["mounts"] if x.get("mounted"))
                    for x in m["mounts"]:
                        if not x.get("mounted"):
                            rec["problems"].append(f"hull cargo {b['berth']}/{x['container']}: {x.get('reason')}")
            except Exception as exc:  # noqa: BLE001
                rec["hull_mounts"][b["berth"]] = {"error": _err(exc)}
                rec["problems"].append(f"hull cargo {b['berth']}: {_err(exc)}")
        print(f"  [{'OK' if n_ok == n_m else 'FAIL'}] hull cargo: {n_ok}/{n_m} studio containers mounted in the hull", flush=True)
    try:
        rec["registry"] = {"berths": R.write()["berth_count"]}
    except Exception as exc:  # noqa: BLE001
        rec["registry"] = {"error": _err(exc)}
        rec["problems"].append(f"bill of lading: {_err(exc)}")
    engines_ok = rec["engines"].get("ok", rec["engines"]["pass"])
    hull_ok = a.no_studio or bool(rec.get("hull", {}).get("installed"))
    faces_ok = all(v.get("ok") for v in rec.get("studio_faces", {}).values())
    ok = engines_ok and hull_ok and faces_ok and not rec["problems"]
    limited = bool(rec["engines"].get("host_limited")) or (not a.no_studio and not rec.get("hull_can_execute", {}).get("ok", True))
    rec["verdict"] = "BUILT" if ok and not limited else "BUILT_HOST_LIMITED" if ok else "FAILED"
    rec["engines_built"] = rec["engines"].get("built")
    os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, indent=2, sort_keys=True, default=str) + "\n")
    # the console gets the summary; the whole record (every berth's face, pictures and mounts) is in the file
    summary = {k: rec.get(k) for k in ("schema", "uc_release", "verdict", "host", "limits", "extract", "hull", "hull_can_execute", "registry")}
    summary["engines"] = {n: {"returncode": v["returncode"], "host_limited": v.get("host_limited")} for n, v in rec["engines"]["nodes"].items()}
    summary["engines_host_adaptations"] = rec["engines"].get("host_adaptations")
    summary["studio_faces"] = {"berths": len(rec.get("studio_faces") or {}), "ok": sum(1 for v in (rec.get("studio_faces") or {}).values() if v.get("ok"))}
    summary["fabric"] = {"available": rec["fabric"]["available"], "reason": rec["fabric"]["reason"], "berths": len(rec["fabric"]["berths"])}
    summary["hull_mounts"] = {"berths": len(rec.get("hull_mounts") or {}),
                              "mounted": sum(1 for b in (rec.get("hull_mounts") or {}).values() for x in b.values() if isinstance(x, dict) and x.get("mounted"))}
    summary["problems"] = rec["problems"][:20] + ([f"... {len(rec['problems']) - 20} more in {out_json}"] if len(rec["problems"]) > 20 else [])
    summary["record"] = out_json
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    print(f"== {rec['verdict']}: engines {len(rec['engines'].get('built') or [])}/4 built"
          + (f" ({', '.join(rec['engines']['built'])})" if rec["engines"].get("built") else "")
          + (f"; hull {'executable' if rec.get('hull_can_execute', {}).get('ok') else 'compile-only'}" if not a.no_studio else "; hull skipped")
          + f"; {len(rec['problems'])} problem(s) -> {out_json}", flush=True)
    return EXIT_OK if ok else EXIT_FAIL


def cmd_load(a) -> int:
    try:
        E.extract_hold()
        rec = BT.load(a.source, a.name, a.kind, notes=a.note, replace=a.replace)
        reg = R.write()
        out = {"schema": "UC/LOAD_RESULT/1", "loaded": rec, "bill_of_lading_berths": reg["berth_count"]}
        if not a.no_studio and E.studio_status().get("installed"):
            from unikernel import studio_face
            try:
                out["studio_face"] = studio_face.register(a.name, rebuild=True)
            except Exception as exc:  # noqa: BLE001 -- the hull's own errors included; the berth is loaded either way
                out["studio_face"] = {"ok": False, "error": _err(exc)}
            if (rec.get("hull_cargo") or []) and any(m.get("name") for m in rec["hull_cargo"]):
                from unikernel import hullmount as HM
                try:
                    out["hull_mounts"] = HM.mount(a.name, force=True)
                except Exception as exc:  # noqa: BLE001
                    out["hull_mounts"] = {"ok": False, "error": _err(exc)}
        out["reseal"] = _reseal(f"load {a.name}", enabled=not a.no_reseal)
        complete = all(out.get(k, {}).get("ok", True) for k in ("studio_face", "hull_mounts"))
        complete = complete and all(m.get('mounted') for m in out.get('hull_mounts', {}).get('mounts', []))
        out["post_load_ok"] = bool(complete)
        return _emit(out, EXIT_OK if complete else EXIT_FAIL, out=a.out)
    except Refusal as exc:
        return _emit({"refused": True, **exc.as_dict()}, EXIT_BLOCKED)
    except ShipError as exc:
        return _emit({"failed": True, **exc.as_dict()}, EXIT_FAIL)


def cmd_unload(a) -> int:
    try:
        if not os.path.isdir(BT.berth_dir(a.name)):
            raise Refusal("no such berth; no mount was changed", {"berth": a.name})
        um = None
        try:
            from unikernel import hullmount as HM
            um = HM.unmount(a.name)
        except Exception as exc:  # noqa: BLE001
            um = {"error": f"{type(exc).__name__}: {exc}"}
        if um and um.get('error'):
            raise Refusal('hull unmount failed; berth unload refused', {'unmount':um})
        r = BT.unload(a.name)
        r["hull_unmounted"] = um
        try:
            from unikernel import studio_face
            s = E.studio()
            if s.installed:
                cn = studio_face.container_name(a.name)
                if cn in {c.get("name") for c in (s.list_containers().get("containers") or [])}:
                    s.remove_container(cn)
                    r["studio_container_removed"] = cn
                # the face's own pictures and state in the studio's state dir
                sd = s.state_dir() if hasattr(s, "state_dir") else None
                if sd and os.path.isdir(sd):
                    gone = []
                    for fn in os.listdir(sd):
                        if fn == f"{cn}.state" or fn.startswith(f"{cn}.fabric."):
                            os.remove(os.path.join(sd, fn))
                            gone.append(fn)
                    r["studio_state_removed"] = gone
        except Exception as exc:  # noqa: BLE001
            raise Refusal('studio removal failed; managed recovery required', {'reason':_err(exc)}) from exc
        R.write()
        r["reseal"] = _reseal(f"unload {a.name}", enabled=not a.no_reseal)
        return _emit(r)
    except Refusal as exc:
        return _emit({"refused": True, **exc.as_dict()}, EXIT_BLOCKED)


def cmd_berths(a) -> int:
    return _emit(R.scan(), out=a.out)


def cmd_sort(a) -> int:
    out = []
    for f in a.files:
        if not os.path.isfile(f):
            return _emit({"rejected": True, "reason": f"no such file {f}"}, EXIT_REJECTED)
        with open(f, "rb") as fh:
            data = fh.read()
        r = sorter.sort_script(os.path.basename(f), data)
        r["rule_text"] = sorter.RULE_TEXT[r["rule"]]
        out.append(r)
    return _emit({"schema": "UC/SORT_EXPLAIN/1", "policy": sorter.POLICY_VERSION, "decisions": out})


def cmd_verify(a) -> int:
    from unikernel import gates
    stamp = _utc()
    out_json = a.out or os.path.join(E.runs_dir(), f"VERIFY_{stamp}{'_' + a.berth if a.berth else ''}.json")
    log_dir = os.path.join(os.path.dirname(out_json), f"VERIFY_{stamp}_logs")
    if a.berth:
        print(f"== UC VERIFY berth {a.berth} -- {UC_RELEASE}", flush=True)
        try:
            res = gates.run_berth_battery(a.berth, log_dir=log_dir, quick=a.quick)
        except Refusal as exc:
            return _emit({"refused": True, **exc.as_dict()}, EXIT_BLOCKED)
    else:
        from unikernel import host as H
        print(f"== UC VERIFY {UC_NAME} -- {UC_RELEASE}", flush=True)
        for k, v in H.limits().items():
            print(f"  [HOST] {k}: {v}", flush=True)
        res = gates.run_ship_battery(log_dir=log_dir, quick=a.quick, hull_verify=not (a.quick or a.no_hull))
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True, default=str)
    t = res["totals"]
    print(f"== {res['verdict']}: {t['passed']} passed, {t['failed']} failed, {t['skipped']} skipped in {t['wall_seconds']}s -> {out_json}", flush=True)
    from unikernel import host as H
    if H.limits():
        print(f"   host limits on this machine: {', '.join(sorted(H.limits()))} -- gates that need what is missing are SKIPPED with the reason "
              f"(README_START_HERE.md > On Windows)", flush=True)
    def skipped_any(value):
        if isinstance(value, dict):
            return value.get("status") == "SKIPPED" or any(skipped_any(v) for v in value.values())
        return isinstance(value, list) and any(skipped_any(v) for v in value)
    if res["verdict"] != "PASS":
        return EXIT_FAIL
    if a.require_complete and skipped_any(res):
        print("== INCOMPLETE: --require-complete refuses skipped gates", flush=True)
        return EXIT_BLOCKED
    return EXIT_OK if res["verdict"] == "PASS" else EXIT_FAIL


def cmd_run(a) -> int:
    d = BT.berth_dir(a.name)
    if not os.path.isdir(d):
        return _emit({"refused": True, "reason": f"no berth {a.name!r}"}, EXIT_BLOCKED)
    from unikernel import ucmanifest as M
    integrity = M.check_sums(d)
    if not integrity["pass"]:
        return _emit({"refused": True, "reason": "berth integrity check failed before execution", "integrity": integrity}, EXIT_BLOCKED)
    try:
        b = E.bind()
    except ShipError as exc:
        return _emit({"blocked": True, **exc.as_dict(), "hint": "run BUILD"}, EXIT_BLOCKED)
    if not b["roots"]:
        return _emit({"blocked": True, "reason": "no engine is bound (run BUILD)"}, EXIT_BLOCKED)
    if not a.sealed:
        return _fabric_ticks(a.name, ticks=max(1, a.ticks or 1), interval=a.interval or 0.0, profile=a.profile, out=a.out, no_view=a.no_view, no_mounts=a.no_mounts)
    FR, lang = b["fabric_runtime"], b["lang"]
    bundle = os.path.join(d, "BERTH.pal" if a.bundle == "BERTH" else "CARGO.pal")
    prog, diags = lang.parse(open(bundle, encoding="utf-8").read())
    if prog is None:
        return _emit({"rejected": True, "diagnostics": [x.as_dict() for x in diags]}, EXIT_REJECTED)
    v = lang.verify(prog)
    if not v.ok:
        return _emit({"rejected": True, "diagnostics": [x.as_dict() for x in v.diagnostics]}, EXIT_REJECTED)
    programs = tuple(p.strip() for p in a.programs.split(",")) if a.programs else ("replica", "pipeline", "bsp")
    seal = json.load(open(os.path.join(d, "BERTH_SEAL.json" if a.bundle == "BERTH" else "CARGO_SEAL.json"), encoding="utf-8"))
    reference = b["witness"].reference_witness_words(b["witness"].words_of(prog))
    if prog.seal() != seal.get("seal") or reference != seal.get("reference_witness") or len(prog.rows) != seal.get("rows"):
        return _emit({"refused": True, "reason": "bundle differs from its pinned seal/reference/row count"}, EXIT_BLOCKED)
    stamp = _utc()
    out = a.out or os.path.join(E.runs_dir(), f"RUN_{stamp}_{a.name}_{a.bundle}.json")
    from unikernel import host as H
    profile, host_note = H.profile_for(a.profile)       # no `fork` on this host: multi_thread_deterministic, and say so
    try:
        run = FR.FabricRun(b["roots"], profile=profile, max_workers=4)
        res = run.run_program(prog, programs=programs, placement=a.placement, source_name=os.path.relpath(bundle, SHIP))
    except b["dfabric"].AdapterRefusal as exc:
        return _emit({"blocked": True, **exc.as_dict()}, EXIT_BLOCKED, out=out)
    res["profile_requested"] = a.profile
    res["host_note"] = host_note
    res["host_adaptations"] = (b.get("host") or {}).get("adaptations")
    seal = json.load(open(os.path.join(d, "BERTH_SEAL.json" if a.bundle == "BERTH" else "CARGO_SEAL.json"), encoding="utf-8"))
    res["pinned_reference_witness"] = seal["reference_witness"]
    res["matches_pinned"] = (res["programs"].get("replica", {}).get("reference_witness", seal["reference_witness"]) == seal["reference_witness"])
    code = EXIT_OK if res["verdict"] == FR.TOKEN_AGREE and res["matches_pinned"] else EXIT_FAIL
    return _emit(res, code, out=out)


def _fabric_ticks(name: str, ticks: int = 1, interval: float = 0.0, profile: str = "single_process_deterministic",
                  out: Optional[str] = None, no_view: bool = False, no_mounts: bool = False) -> int:
    """`uc run` / `uc fabric tick|live`: N ticks of the berth's fabric, every picture in, executed, out."""
    import time as _time
    from unikernel import tif_fabric as TF
    ok, why = TF.available()
    if not ok:
        return _emit({"blocked": True, "reason": why, "hint": "install Pillow (see REQUIREMENTS.txt); `uc run NAME --sealed` runs the sealed bundles without it"}, EXIT_BLOCKED)
    stamp = _utc()
    out = out or os.path.join(E.runs_dir(), f"RUN_{stamp}_{name}_tick.json")
    recs = []
    code = EXIT_OK
    try:
        for i in range(ticks):
            r = TF.tick(name, profile=profile, view=not no_view, log_dir=None, mounts=not no_mounts)
            recs.append(r)
            sm = r["summary"]
            print(f"  tick {i + 1}/{ticks}: {r['verdict']} -- {sm['containers_ticked']}/{sm['of']} pictures ticked"
                  + (f" + {sm['hull_mounts_ticked']}/{sm['hull_mounts']} hull cargo" if sm.get('hull_mounts') else "")
                  + f", unanimous={sm['unanimous']}, declaration_intact={sm['all_intact']}, hull_face_ok={sm['hull_face_ok']}, event_log={sm['event_log_hash'][:16]}.. ({sm['wall_s']}s)", flush=True)
            if r["verdict"] == "TICK_INCOMPLETE":
                code = EXIT_BLOCKED
            elif r["verdict"] != "TICK_OK" and code == EXIT_OK:
                code = EXIT_FAIL
            if interval and i + 1 < ticks:
                _time.sleep(interval)
    except (ShipError, Refusal) as exc:
        return _emit({"blocked": True, **exc.as_dict()}, EXIT_BLOCKED, out=out)
    except b_adapter_refusal() as exc:  # noqa: B030
        return _emit({"blocked": True, **exc.as_dict()}, EXIT_BLOCKED, out=out)
    result = recs[-1] if len(recs) == 1 else {"schema": "UC/FABRIC_LIVE/1", "berth": name, "ticks": len(recs), "last": recs[-1],
                                                "history": [{"tick_utc": r["utc"], "verdict": r["verdict"], **r["summary"]} for r in recs]}
    return _emit(result, code, out=out)


def b_adapter_refusal():
    try:
        return E.bind()["dfabric"].AdapterRefusal
    except Exception:  # noqa: BLE001
        return ShipError


def cmd_fabric(a) -> int:
    from unikernel import tif_fabric as TF
    d = BT.berth_dir(a.name)
    if not os.path.isdir(d):
        return _emit({"refused": True, "reason": f"no berth {a.name!r}"}, EXIT_BLOCKED)
    ok, why = TF.available()
    if not ok:
        return _emit({"blocked": True, "reason": why, "hint": "install Pillow (see REQUIREMENTS.txt)"}, EXIT_BLOCKED)
    try:
        if a.verb == "init":
            return _emit({"schema": "UC/FABRIC_INIT/1", **TF.init_live(a.name, force=a.force)})
        if a.verb in ("tick", "live"):
            n = a.ticks or (1 if a.verb == "tick" else 10)
            return _fabric_ticks(a.name, ticks=n, interval=(a.interval if a.interval is not None else (0.5 if a.verb == "live" else 0.0)),
                                 profile=a.profile, out=a.out, no_view=a.no_view, no_mounts=a.no_mounts)
        if a.verb == "status":
            return _emit(TF.status(a.name), out=a.out)
        if a.verb == "view":
            return _emit({"schema": "UC/FABRIC_VIEW/1", **TF.views(a.name, scale=a.scale)}, out=a.out)
        if a.verb == "frames":
            return _emit({"schema": "UC/FABRIC_FRAMES/1", **TF.frames(a.name)}, out=a.out)
    except (ShipError, Refusal) as exc:
        return _emit({"blocked": True, **exc.as_dict()}, EXIT_BLOCKED)
    return _emit({"rejected": True, "reason": f"unknown fabric verb {a.verb!r}"}, EXIT_REJECTED)


def cmd_mount(a) -> int:
    from unikernel import hullmount as HM
    d = BT.berth_dir(a.name)
    if not os.path.isdir(d):
        return _emit({"refused": True, "reason": f"no berth {a.name!r}"}, EXIT_BLOCKED)
    try:
        r = HM.mount(a.name, force=a.force, trust=not a.no_trust)
        return _emit({"schema": "UC/HULL_MOUNT/1", **r}, EXIT_OK if r["ok"] else EXIT_FAIL, out=a.out)
    except (ShipError, Refusal) as exc:
        return _emit({"blocked": True, **exc.as_dict()}, EXIT_BLOCKED)


def cmd_mounts(a) -> int:
    from unikernel import hullmount as HM
    d = BT.berth_dir(a.name)
    if not os.path.isdir(d):
        return _emit({"refused": True, "reason": f"no berth {a.name!r}"}, EXIT_BLOCKED)
    return _emit({"schema": "UC/HULL_MOUNTS_STATUS/1", **HM.status(a.name)}, out=a.out)


def cmd_slot_run(a) -> int:
    d = BT.berth_dir(a.name)
    slot = a.slot
    if slot not in SLOTS or slot == "DF_Fabric":
        return _emit({"rejected": True, "reason": f"slot must be one of {[s for s in SLOTS if s != 'DF_Fabric']}"}, EXIT_REJECTED)
    nid = next(n for n, c in NODE_CONTAINER.items() if c == slot)
    SAFE.relative_path(a.cargo)
    from unikernel import ucmanifest as M
    with open(os.path.join(d, "SORT_LEDGER.json"), encoding="utf-8") as fh:
        ledger = json.load(fh)
    choices = [r for r in ledger["records"] if r.get("node") == nid and a.cargo in (r.get("path"), BT.stored_path_of(r))]
    if len(choices) != 1:
        return _emit({"rejected": True, "reason": "cargo must identify exactly one ledger entry in the requested slot"}, EXIT_REJECTED)
    cargo = choices[0]
    p = SAFE.contained_path(d, slot + "/cargo/" + BT.stored_path_of(cargo))
    if not os.path.isfile(p) or M.sha256_file(p) != cargo["sha256"] or os.path.getsize(p) != cargo["bytes"]:
        return _emit({"refused": True, "reason": "cargo is missing or differs from its registered bytes"}, EXIT_BLOCKED)
    try:
        b = E.bind()
    except ShipError as exc:
        return _emit({"blocked": True, **exc.as_dict()}, EXIT_BLOCKED)
    if nid not in b["roots"]:
        return _emit({"blocked": True, "reason": f"engine {nid} is not bound (run BUILD)"}, EXIT_BLOCKED)
    ad = b["nodes"].make_adapter(nid, b["roots"][nid])
    try:
        with open(p, "rb") as fh:
            is_pa = fh.read(9).startswith(b"#PA-LCTL/")
        if a.cargo.endswith(".pal") or is_pa:
            with open(p, encoding="utf-8") as fh:
                source_text = fh.read()
            prog, diags = b["lang"].parse(source_text)
            if prog is None or not b["lang"].verify(prog).ok:
                return _emit({"rejected": True, "reason": "bundle did not parse/verify"}, EXIT_REJECTED)
            r = ad.submit(prog)
            return _emit({"schema": "UC/SLOT_RUN/1", "berth": a.name, "slot": slot, "cargo": a.cargo, "kind": "row_sequence_witness", "result": r},
                         EXIT_OK if r.get("halted") and r.get("native_witness") == r.get("reference_witness") else EXIT_FAIL)
        r = ad.run_native(p, max_steps=a.max_steps)
        return _emit({"schema": "UC/SLOT_RUN/1", "berth": a.name, "slot": slot, "cargo": a.cargo, "kind": "native_guest_program", "result": r},
                     EXIT_OK if r.get("halted") else EXIT_FAIL)
    except b["dfabric"].AdapterRefusal as exc:
        return _emit({"blocked": True, "berth": a.name, "slot": slot, "cargo": a.cargo, **exc.as_dict()}, EXIT_BLOCKED)


def cmd_studio_register(a) -> int:
    from unikernel import studio_face
    try:
        result = studio_face.register(a.name, rebuild=True)
        return _emit(result, EXIT_OK if result.get("ok") else EXIT_FAIL)
    except (ShipError, Refusal) as exc:
        return _emit({"blocked": True, **exc.as_dict()}, EXIT_BLOCKED)


def cmd_studio_test(a) -> int:
    from unikernel import studio_face
    r = studio_face.test_all()
    return _emit(r, EXIT_BLOCKED if r.get("skipped") else EXIT_OK if r.get("ok") else EXIT_FAIL)


def cmd_doctor(a) -> int:
    from unikernel import diagnostics
    rec = diagnostics.doctor()
    return _emit(rec, EXIT_OK if rec["preflight_ok"] else EXIT_BLOCKED, out=a.out)


def cmd_self_test(a) -> int:
    import subprocess
    return subprocess.call([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "discover", "-s", os.path.join(SHIP, "tests"), "-v"], cwd=SHIP)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="uc", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=UC_RELEASE)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("status"); p.add_argument("--out"); p.set_defaults(fn=cmd_status)
    p = sp.add_parser("build"); p.add_argument("--pa21", help="PA21 delivery root for the hull's ledger bridge (default hold/PA21_LEDGER_EXCERPT)")
    p.add_argument("--no-studio", action="store_true"); p.add_argument("--force", action="store_true"); p.add_argument("--out"); p.set_defaults(fn=cmd_build)
    p = sp.add_parser("load"); p.add_argument("source"); p.add_argument("--name", required=True); p.add_argument("--kind", choices=("vm", "subsystem"), default="subsystem")
    p.add_argument("--replace", action="store_true"); p.add_argument("--note"); p.add_argument("--no-studio", action="store_true")
    p.add_argument("--no-reseal", action="store_true", help="do not re-seal the ship after loading (VERIFY U0.1/U0.2 will then FAIL until `uc seal`)")
    p.add_argument("--out"); p.set_defaults(fn=cmd_load)
    p = sp.add_parser("unload"); p.add_argument("name"); p.add_argument("--no-reseal", action="store_true"); p.set_defaults(fn=cmd_unload)
    p = sp.add_parser("seal"); p.add_argument("--reason"); p.add_argument("--out"); p.set_defaults(fn=cmd_seal)
    p = sp.add_parser("berths"); p.add_argument("--out"); p.set_defaults(fn=cmd_berths)
    p = sp.add_parser("sort"); p.add_argument("files", nargs="+"); p.set_defaults(fn=cmd_sort)
    p = sp.add_parser("verify"); p.add_argument("berth", nargs="?"); p.add_argument("--quick", action="store_true"); p.add_argument("--no-hull", action="store_true"); p.add_argument("--require-complete", action="store_true", help="fail when any ship or nested berth gate is skipped"); p.add_argument("--out"); p.set_defaults(fn=cmd_verify)
    p = sp.add_parser("run"); p.add_argument("name"); p.add_argument("--sealed", action="store_true", help="run the sealed bundles' programs (replica/pipeline/bsp) instead of ticking the .tif fabric")
    p.add_argument("--ticks", type=int, help="fabric ticks to run (default 1)"); p.add_argument("--interval", type=float, help="seconds between ticks")
    p.add_argument("--no-view", action="store_true", help="do not render the PNG views after the tick")
    p.add_argument("--no-mounts", action="store_true", help="tick the berth's six pictures only, not the studio containers it carries (hull cargo)")
    p.add_argument("--programs"); p.add_argument("--profile", default="single_process_deterministic",
        choices=("single_process_deterministic", "multi_thread_deterministic", "multi_process_deterministic", "multi_process_throughput"))
    p.add_argument("--placement", default="static", choices=("static", "dynamic")); p.add_argument("--bundle", default="BERTH", choices=("BERTH", "CARGO")); p.add_argument("--out"); p.set_defaults(fn=cmd_run)
    p = sp.add_parser("fabric"); p.add_argument("verb", choices=("init", "tick", "live", "status", "view", "frames")); p.add_argument("name")
    p.add_argument("--force", action="store_true", help="init: reset the live images to the sealed genesis (and the hull face's image to empty)")
    p.add_argument("--ticks", type=int); p.add_argument("--interval", type=float); p.add_argument("--no-view", action="store_true"); p.add_argument("--no-mounts", action="store_true"); p.add_argument("--scale", type=int, default=16)
    p.add_argument("--profile", default="single_process_deterministic",
        choices=("single_process_deterministic", "multi_thread_deterministic", "multi_process_deterministic", "multi_process_throughput"))
    p.add_argument("--out"); p.set_defaults(fn=cmd_fabric)
    p = sp.add_parser("mount"); p.add_argument("name"); p.add_argument("--force", action="store_true"); p.add_argument("--no-trust", action="store_true"); p.add_argument("--out"); p.set_defaults(fn=cmd_mount)
    p = sp.add_parser("mounts"); p.add_argument("name"); p.add_argument("--out"); p.set_defaults(fn=cmd_mounts)
    p = sp.add_parser("slot-run"); p.add_argument("name"); p.add_argument("slot"); p.add_argument("cargo"); p.add_argument("--max-steps", type=int); p.set_defaults(fn=cmd_slot_run)
    p = sp.add_parser("studio-register"); p.add_argument("name"); p.set_defaults(fn=cmd_studio_register)
    p = sp.add_parser("studio-test"); p.set_defaults(fn=cmd_studio_test)
    p = sp.add_parser("doctor", help="offline preflight and explicit capability boundaries")
    p.add_argument("--out"); p.set_defaults(fn=cmd_doctor)
    p = sp.add_parser("self-test", help="run the ship-layer regression suite")
    p.set_defaults(fn=cmd_self_test)
    from . import foundation_cli
    foundation_cli.configure(sp)
    from . import vws_cli
    vws_cli.configure(sp)
    from . import pixels_cli
    pixels_cli.configure(sp)
    from . import tiff_workflow
    tiff_workflow.configure(sp)
    from . import onebit_cli
    onebit_cli.configure(sp)
    from . import onebit_workflow
    onebit_workflow.configure(sp)
    from . import master_workflow
    master_workflow.configure(sp)
    from . import platform_cli
    platform_cli.configure(sp)
    from . import edge_atoms
    edge_atoms.configure(sp)
    for parser in sp.choices.values():
        if parser.prog.split()[-1] in {'load','unload','run','slot-run','fabric','mount','studio-register'}:
            parser.add_argument('--generation', type=int, help='refuse a stale local workload generation before execution')
        if parser.prog.split()[-1] in {'run','slot-run','fabric','mount','build'}:
            parser.add_argument('--require-isolation', choices=('host-process','hypervisor'), default='host-process',
                                help='required execution class; unavailable stronger isolation is refused')
    a = ap.parse_args(argv)
    try:
        for key in ("name", "berth"):
            value = getattr(a, key, None)
            if value is not None:
                SAFE.validate_name(value)
        if getattr(a, "ticks", None) is not None:
            SAFE.finite_number(a.ticks, 1, 10000, "ticks")
        if getattr(a, "interval", None) is not None:
            SAFE.finite_number(a.interval, 0, 86400, "interval")
        if getattr(a, "scale", None) is not None:
            SAFE.finite_number(a.scale, 1, 64, "scale")
        if getattr(a, "max_steps", None) is not None:
            SAFE.finite_number(a.max_steps, 1, 10000000, "max_steps")
        if getattr(a, "programs", None) is not None:
            programs = a.programs.split(",")
            if not programs or any(p.strip() not in ("replica", "pipeline", "bsp") for p in programs):
                raise Refusal("programs must be a comma-separated subset of replica,pipeline,bsp")
        if a.cmd in {"self-test", "terminal"} or (a.cmd == "master-workflow" and getattr(a, "verb", None) == "execute") \
                or (a.cmd == "edge" and getattr(a, "edge_verb", None) == "test"):
            return a.fn(a)  # test/service parents must not hold the ship lock while children acquire it
        with SAFE.ship_lock(E.ship_root()):
            from . import transactions as TX, contracts as C
            if getattr(a, 'require_isolation', None):
                C.require_backend(a.require_isolation)
            if getattr(a, 'generation', None) is not None:
                from .control_store import generation, ControlStore
                generation(a.generation)
                existing = ControlStore(E.ship_root()).inspect(getattr(a,'name',None))['workloads']
                actual = existing[0]['generation'] if existing else 1
                if a.generation != actual:
                    raise Refusal('stale generation refused before mutation', {'expected':a.generation,'actual':actual})
            protected = a.cmd in {'build','load','unload','run','slot-run','mount','studio-register','seal','studio-test','verify'}
            protected = protected or (a.cmd == 'fabric' and a.verb in {'init','tick','live','view'})
            protected = protected or (a.cmd == 'pixels' and a.pixel_verb in {'paint','checkpoint'})
            protected = protected or (a.cmd == 'onebit' and a.onebit_verb == 'tiff-put')
            if protected:
                return TX.execute(E.ship_root(), a, a.fn)
            return a.fn(a)
    except Refusal as exc:
        return _emit({"refused": True, **exc.as_dict()}, EXIT_BLOCKED)
    except ShipError as exc:
        return _emit({"failed": True, **exc.as_dict()}, EXIT_FAIL)
    except KeyboardInterrupt:
        return _emit({"interrupted": True, "reason": "operator interrupted the command"}, 130)
    except Exception as exc:
        # Preserve a traceback locally, but make expected console failures actionable.
        import traceback
        path = os.path.join(E.runs_dir(), f"ERROR_{_utc()}.log")
        try:
            SAFE.atomic_write(path, traceback.format_exc())
        except OSError:
            path = None
        return _emit({"failed": True, "error": _err(exc), "diagnostic": path}, EXIT_FAIL)


if __name__ == "__main__":
    sys.exit(main())
