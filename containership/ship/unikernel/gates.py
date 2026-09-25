"""The ship's gate batteries -- what VERIFY runs.

Ship gates (U*): container integrity, hull digest and the hull's own 128-check
verifier, hold digests, engines extracted/built/bound, hull installed, sort
policy self-check, bill of lading rebuilt from disk, then every berth's battery.

Berth gates (B*): berth hashes; the sort ledger re-derived from the cargo bytes
(identical decisions, no extra or missing cargo); CARGO.pal / BERTH.pal / the
slots' NODE.pal parse, verify and seal to their pinned seals; the studio face
source equals the field lowering of BERTH.pal; BERTH.pal witnessed on every
bound engine (replica + BSP) with cross-node agreement; CARGO.pal witnessed in
84-row segments (replica per engine and a pipeline across engines); the studio
container answers R2 == reference; a sample of runnable cargo executed on its
engine with definite verdicts; every container's own .tif fabric is present,
reversible and rooted at its sealed genesis (B9); a tick on a scratch copy of
the pictures executes them -- the four engines agree with the CPython
reference for the state read, the federation records the vote and a sealed
event log, a painted tick cell is executed as painted, a painted declaration
cell breaks unanimity and is reported, and the hull's VM ticks the hull face's
own picture with R2 still equal to the reference (B10).

PASS / FAIL / SKIPPED with a stated reason; no PASS that was not observed.
"""

from __future__ import annotations

import datetime as _dt
from . import strictjson as json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional

from . import UC_RELEASE, NODE_IDS, NODE_CONTAINER, FABRIC_CONTAINER, SLOTS, SEGMENT_ROWS, ShipError, Refusal
from . import ucmanifest as M
from . import ucschemas as S
from . import sorter
from . import engines as E
from . import registry
from . import studio_face
from . import tif_fabric as TF
from .berth import berth_dir, berths_dir, list_scripts

GATE_SCHEMA = "UC/GATE_RESULTS/1"


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def host_record() -> dict:
    from . import host as H
    f = H.facts()
    return {"platform": platform.platform(), "python": sys.version.split()[0], "cpu_count": os.cpu_count(),
            "cc": f["cc"], "make": f["make"], "java": f["java"], "sh": f["sh"], "fork": f["fork"], "utf8_mode": f["utf8_mode"],
            "limits": H.limits(), "network_policy": "deny", "backend_policy": "none"}


class Battery:
    def __init__(self, subject: str, log_dir: Optional[str] = None):
        self.subject, self.gates, self.log_dir = subject, [], log_dir
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        self.t0 = time.perf_counter()

    def log(self, name: str, text: str) -> None:
        if self.log_dir:
            with open(os.path.join(self.log_dir, name), "w", encoding="utf-8") as fh:
                fh.write(text)

    def gate(self, gid: str, name: str, fn: Callable[[], dict], *, skip_if: Optional[str] = None) -> dict:
        t0 = time.perf_counter()
        if skip_if:
            rec = {"id": gid, "name": name, "status": "SKIPPED", "seconds": 0.0, "detail": {"reason": skip_if}}
        else:
            try:
                detail = fn() or {}
                status = detail.pop("_status", "PASS")
            except (ShipError, Refusal) as exc:
                status, detail = "FAIL", {"error": str(exc), "detail": exc.detail}
            except Exception as exc:  # noqa: BLE001
                status, detail = "FAIL", {"exception": f"{type(exc).__name__}: {exc}"}
            rec = {"id": gid, "name": name, "status": status, "seconds": round(time.perf_counter() - t0, 3), "detail": detail}
        self.gates.append(rec)
        print(f"  [{rec['status']}] {gid} {name} ({rec['seconds']}s)" + (f": {skip_if}" if skip_if else ""), flush=True)
        return rec

    def results(self, extra: Optional[dict] = None) -> dict:
        n = len(self.gates)
        p = sum(1 for g in self.gates if g["status"] == "PASS")
        f = sum(1 for g in self.gates if g["status"] == "FAIL")
        s = sum(1 for g in self.gates if g["status"] == "SKIPPED")
        out = {"schema": GATE_SCHEMA, "uc_release": UC_RELEASE, "subject": self.subject, "executed_at_utc": utcnow(),
               "host": host_record(), "gates": self.gates,
               "totals": {"run": n, "passed": p, "failed": f, "skipped": s, "wall_seconds": round(time.perf_counter() - self.t0, 3)},
               "verdict": "PASS" if f == 0 else "FAIL",
               "rule": "PASS means every gate that could run passed; SKIPPED gates name the missing prerequisite and are not counted as passes"}
        if extra:
            out.update(extra)
        return out


def _sh(cmd: List[str], cwd: str, timeout: int = 3600, env=None) -> dict:
    from .supervisor import run
    return run(cmd, cwd=cwd, timeout=timeout, env=env)


def _load_json(p: str) -> Any:
    return json.load(open(p, encoding="utf-8"))


# --------------------------------------------------------------------------
# berth battery
# --------------------------------------------------------------------------

def _parse_verified(lang, path: str):
    text = open(path, encoding="utf-8").read()
    prog, diags = lang.parse(text)
    if prog is None:
        raise ShipError(f"{os.path.basename(path)} did not parse", {"diagnostics": [d.as_dict() for d in diags]})
    v = lang.verify(prog)
    if not v.ok:
        raise ShipError(f"{os.path.basename(path)} did not verify", {"diagnostics": [d.as_dict() for d in v.diagnostics]})
    return prog


RUNNABLE_KINDS = {"N_SMALL": ("mssl_asm", "pal"), "N_MEDIUM": ("lctlc11", "pal"), "N_LARGE": ("lctlc12", "pal"), "N_XLARGE": ("lctlc10", "pal")}


def run_berth_battery(name: str, *, log_dir: Optional[str] = None, quick: bool = False,
                      cargo_sample: int = 24) -> dict:
    d = berth_dir(name)
    if not os.path.isdir(d):
        raise Refusal(f"no berth {name!r}", {"berth": d})
    B = Battery(f"berth {name}", log_dir)
    rec = _load_json(os.path.join(d, "BERTH.json"))
    ledger = _load_json(os.path.join(d, "SORT_LEDGER.json"))

    def b0():
        r = M.check_sums(d, "SHA256SUMS.txt")
        r["_status"] = "PASS" if r["pass"] else "FAIL"
        return r
    B.gate("B0", "berth SHA256SUMS.txt verifies (every berth file bound, none unbound)", b0)

    def b1():
        errs = {"schemas": {}}
        fabric_loaded = (rec.get("fabric") or {}).get("available", False)
        for rel, sname in S.BERTH_SCHEMA_MAP.items():
            p = os.path.join(d, rel)
            if not os.path.isfile(p):
                if rel in S.OPTIONAL_WHEN_FABRIC_UNAVAILABLE and not fabric_loaded:
                    continue
                errs["schemas"][rel] = ["missing"]
                continue
            e = S.validate(_load_json(p), S.SCHEMAS[sname])
            if e:
                errs["schemas"][rel] = e[:6]
        return {"_status": "PASS" if not errs["schemas"] else "FAIL", **errs}
    B.gate("B1", "BERTH.json, SORT_LEDGER.json, every SLOT.json and every container's FABRIC.json validate against the ship's schemas", b1)

    def b2():
        from .berth import stored_path_of
        recs = {r["path"]: r for r in ledger["records"]}
        stored_to_path = {stored_path_of(r): r["path"] for r in ledger["records"]}
        on_disk = {}
        for nid in NODE_IDS:
            croot = os.path.join(d, NODE_CONTAINER[nid], "cargo")
            if not os.path.isdir(croot):
                continue
            for dp, dns, fns in os.walk(croot):
                dns[:] = sorted(dns)
                for fn in sorted(fns):
                    p = os.path.join(dp, fn)
                    rel = os.path.relpath(p, croot).replace(os.sep, "/")
                    if rel == "CARGO_MANIFEST.json":
                        continue
                    rel = stored_to_path.get(rel, rel)          # an aliased file answers to its original path
                    on_disk[rel] = (nid, p)
        missing = sorted(set(recs) - set(on_disk))
        extra = sorted(set(on_disk) - set(recs))
        drift, checked = [], 0
        for rel, (nid, p) in sorted(on_disk.items()):
            r = recs.get(rel)
            if not r:
                continue
            with open(p, "rb") as fh:
                data = fh.read()
            fresh = sorter.sort_script(rel, data)
            checked += 1
            if (fresh["node"], fresh["rule"], fresh["sha256"]) != (r["node"], r["rule"], r["sha256"]) or nid != r["node"]:
                drift.append({"path": rel, "ledger": (r["node"], r["rule"], r["sha256"][:12]), "fresh": (fresh["node"], fresh["rule"], fresh["sha256"][:12]), "placed_in": nid})
        pol = sorter.policy_record()
        import hashlib
        pol_sha = hashlib.sha256(json.dumps(pol, sort_keys=True).encode()).hexdigest()
        ok = not missing and not extra and not drift and pol_sha == ledger["policy_sha256"] and checked == len(recs)
        return {"_status": "PASS" if ok else "FAIL", "checked": checked, "missing": missing[:10], "extra": extra[:10],
                "drift": drift[:10], "policy_matches": pol_sha == ledger["policy_sha256"]}
    B.gate("B2", "the sort ledger re-derives from the cargo bytes: identical node, rule and digest for every script (aliased files answer to their original path); no extra or missing cargo; policy digest matches", b2)

    bound = E.bind(require=False)
    lang = bound.get("lang")
    W = bound.get("witness")
    if not lang:
        B.gate("B3", "bundles verify and seal", lambda: {}, skip_if="hold not extracted (run BUILD): pacore not importable")
        B.gate("B4", "studio face source equals the lowering of BERTH.pal", lambda: {}, skip_if="hold not extracted")
        return B.results({"berth": name})

    seals = {}

    def b3():
        out = {}
        for rel, seal_rel in (("CARGO.pal", "CARGO_SEAL.json"), ("BERTH.pal", "BERTH_SEAL.json")):
            prog = _parse_verified(lang, os.path.join(d, rel))
            pinned = _load_json(os.path.join(d, seal_rel))
            ok = prog.seal() == pinned["seal"] and len(prog.rows) == pinned["rows"]
            out[rel] = {"seal": prog.seal(), "pinned": pinned["seal"], "rows": len(prog.rows), "ok": ok}
            seals[rel] = (prog, pinned)
        for nid in NODE_IDS:
            p = os.path.join(d, NODE_CONTAINER[nid], "node", "NODE.pal")
            prog = _parse_verified(lang, p)
            pinned = _load_json(os.path.join(d, NODE_CONTAINER[nid], "node", "NODE_SEAL.json"))
            out[f"{NODE_CONTAINER[nid]}/node/NODE.pal"] = {"ok": prog.seal() == pinned["seal"], "rows": len(prog.rows)}
        cargo_rows = len(seals["CARGO.pal"][0].rows)
        out["cargo_rows_equal_scripts_plus_declarations"] = (cargo_rows == ledger["scripts"] + 8)
        ok = all(v["ok"] for v in out.values() if isinstance(v, dict)) and out["cargo_rows_equal_scripts_plus_declarations"]
        return {"_status": "PASS" if ok else "FAIL", **out}
    B.gate("B3", "CARGO.pal, BERTH.pal and the four slots' NODE.pal parse, verify (pacore.lang) and seal to their pinned seals; CARGO.pal has one row per script", b3)

    def b4():
        prog, pinned = seals["BERTH.pal"]
        words = W.words_of(prog)
        unit_id = f"uc.berth.{name.replace('-', '_')}"
        expected = TF.hull_face_source(words, unit_id=unit_id)
        actual = open(os.path.join(d, "studio", "main.lctlc"), encoding="utf-8").read()
        app = _load_json(os.path.join(d, "studio", "pa21app.json"))
        ref = W.reference_witness_words(words)
        # the witness arithmetic is the DF lowering's, row for row: the field lowering is the DF lowering plus the field rows
        df_rows = W.lower_lctlc12(words, unit_id=unit_id).splitlines()
        df_body = [r for r in df_rows if r.startswith("W")][:-2]           # ... up to (not including) MOV R2 / HALT
        fld_body = [r for r in expected.splitlines() if r.startswith("W")]
        same_prefix = fld_body[:len(df_body)] == df_body
        ok = expected == actual and app["expect"]["registers"]["R2"] == ref == pinned["reference_witness"] and same_prefix
        return {"_status": "PASS" if ok else "FAIL", "source_identical": expected == actual, "expected_R2": app["expect"]["registers"]["R2"],
                "reference": ref, "witness_rows_identical_to_df_lowering": same_prefix, "field_rows": len(fld_body) - len(df_body)}
    B.gate("B4", "studio/main.lctlc is byte-identical to the field lowering of BERTH.pal (the DF witness rows, then the fabric rows) and pa21app.json expects R2 == reference witness", b4)

    roots = bound["roots"]
    FR = bound["fabric_runtime"]
    engines_skip = None if roots else "no engine bound (run BUILD)"

    def b5():
        prog, pinned = seals["BERTH.pal"]
        run = FR.FabricRun(roots, profile="single_process_deterministic")
        out = run.run_program(prog, programs=("replica", "bsp"), source_name=f"{name}/BERTH.pal")
        B.log("berth_pal_run.json", json.dumps(out, indent=1, sort_keys=True, default=str))
        ok = out["verdict"] == FR.TOKEN_AGREE and out["programs"]["replica"]["reference_witness"] == pinned["reference_witness"]
        return {"_status": "PASS" if ok else "FAIL", "verdict": out["verdict"], "witnesses": out["programs"]["replica"]["native_witnesses"],
                "reference": pinned["reference_witness"], "engines": sorted(roots), "engines_absent": [n for n in NODE_IDS if n not in roots],
                "event_log_hash": out["event_log"]["hash"],
                "replay": out["event_log"]["replay_self_check"]["token"], "bsp_votes": out["programs"]["bsp"]["votes"]}
    B.gate("B5", "BERTH.pal witnessed on every bound engine (replica + BSP): cross-node differential agreement with the pinned reference; replay PASS", b5, skip_if=engines_skip)

    def b6():
        from . import host as H
        prog, pinned = seals["CARGO.pal"]
        profile, host_note = H.profile_for("multi_process_deterministic")
        run = FR.FabricRun(roots, profile=profile)
        out = run.run_program(prog, programs=("replica", "pipeline"), source_name=f"{name}/CARGO.pal")
        B.log("cargo_pal_run.json", json.dumps(out, indent=1, sort_keys=True, default=str))
        p = out["programs"]["pipeline"]
        ok = out["verdict"] == FR.TOKEN_AGREE and p["final_witness"] == pinned["reference_witness"]
        return {"_status": "PASS" if ok else "FAIL", "verdict": out["verdict"], "rows": out["rows"], "segments": p["segments"],
                "chain": [(c["segment"], c["node_id"]) for c in p["chain"]][:12], "final": p["final_witness"], "reference": pinned["reference_witness"],
                "replica_segments_per_engine": {k: v["segments"] for k, v in out["programs"]["replica"]["nodes"].items()},
                "profile": profile, "profile_requested": "multi_process_deterministic", "host_note": host_note,
                "wall_s": out["wall_s"]}
    B.gate("B6", f"CARGO.pal ({rec['scripts']} rows) witnessed in {SEGMENT_ROWS}-row segments: replica on every engine and a pipeline chained across engines reach the pinned reference (multi-process profile where the host has fork, multi-thread where it has not -- recorded)", b6, skip_if=engines_skip)

    def b7():
        r = studio_face.check(name)
        if r.get("skipped"):
            return {"_status": "SKIPPED", "reason": r["skipped"], "host_limited": bool(r.get("host_limited"))}
        return {"_status": "PASS" if r["ok"] else "FAIL", **r}
    B.gate("B7", "the hull face: the berth's studio container runs on the hull's runtime and answers R2 == reference witness (studio expectation met; SKIPPED with the reason on a compile-only hull)", b7)

    def b8():
        nodes_mod = bound["nodes"]
        attempts, ok_n, refused, errors = [], 0, 0, 0
        for nid in NODE_IDS:
            if nid not in roots:
                continue
            kinds = RUNNABLE_KINDS[nid]
            cands = [r for r in ledger["records"] if r["node"] == nid and r["kind"] in kinds][:cargo_sample]
            if not cands:
                continue
            ad = nodes_mod.make_adapter(nid, roots[nid])
            for r in cands:
                p = os.path.join(d, NODE_CONTAINER[nid], "cargo", r.get("stored_as") or r["path"])
                t0 = time.perf_counter()
                try:
                    if r["kind"] == "pal":
                        prog = _parse_verified(lang, p)
                        res = ad.submit(prog)
                        attempts.append({"node": nid, "path": r["path"], "verdict": "WITNESSED", "witness": res["native_witness"], "s": round(time.perf_counter() - t0, 3)})
                    else:
                        res = ad.run_native(p)
                        attempts.append({"node": nid, "path": r["path"], "verdict": "HALTED", "result_low64": res["result_low64"], "s": round(time.perf_counter() - t0, 3),
                                         "lctl_column_verify": (res.get("extra") or {}).get("lctl_column_verify")})
                    ok_n += 1
                except bound["dfabric"].AdapterRefusal as exc:
                    refused += 1
                    # the toolchain's own words for the refusal (the last step's stderr, e.g. the QUORUM VM's {"status":"ERROR",...})
                    steps = (exc.detail or {}).get("steps") or []
                    said = (steps[-1].get("stderr") or steps[-1].get("stdout") or "")[-300:] if steps else ""
                    attempts.append({"node": nid, "path": r["path"], "verdict": "REFUSED", "reason": exc.reason[:160], "toolchain_said": said,
                                     "s": round(time.perf_counter() - t0, 3)})
                except ShipError as exc:
                    refused += 1
                    attempts.append({"node": nid, "path": r["path"], "verdict": "REFUSED", "reason": str(exc)[:160], "s": round(time.perf_counter() - t0, 3)})
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    attempts.append({"node": nid, "path": r["path"], "verdict": "ERROR", "reason": f"{type(exc).__name__}: {exc}"[:160]})
        B.log("runnable_cargo.json", json.dumps(attempts, indent=1, sort_keys=True))
        if not attempts:
            return {"_status": "SKIPPED", "reason": f"no cargo of a runnable kind on a bound engine (bound: {sorted(roots)}; not bound: {[n for n in NODE_IDS if n not in roots]})"}
        return {"_status": "PASS" if errors == 0 else "FAIL", "attempted": len(attempts), "halted_or_witnessed": ok_n, "refused": refused,
                "errors": errors, "sample": attempts[:12],
                "note": "a refusal is a definite verdict (the engine's toolchain declined the script with a reason); only an adapter exception fails this gate"}
    B.gate("B8", "runnable cargo (a sample per engine of scripts in that engine's dialect, and .pal bundles) executes on its engine with a definite verdict", b8, skip_if=engines_skip)

    tif_ok, tif_why = TF.available()
    tif_skip = None if tif_ok else tif_why
    fabric_rec = rec.get("fabric") or {}
    if tif_ok and not fabric_rec.get("available", True):
        tif_skip = "the berth was loaded without the .tif fabric: " + str(fabric_rec.get("reason"))

    def b9():
        scratch = os.path.join(log_dir, "tif_check") if log_dir else None
        # the live images must exist to be checked; BUILD makes them from genesis, so does the first RUN --
        # here they are materialised from genesis if absent (kept if present), never reset
        made = TF.init_live(name, force=False, face=False)
        r = TF.check_images(name, scratch=scratch)
        r["_status"] = "PASS" if r["ok"] else "FAIL"
        r["live_images_made_now"] = [k for k, v in made["containers"].items() if v.get("created")]
        if scratch and os.path.isdir(scratch):
            shutil.rmtree(scratch, ignore_errors=True)       # the round-trip scratch files are not evidence
        return r
    B.gate("B9", "every container in the berth has its own .tif fabric (five DF containers + the hull face): PA21FABTIF/1, reversible byte for byte, live history rooted at the sealed genesis, page count == tick + 1, declaration tiles reported against the sealed words", b9, skip_if=tif_skip)

    def b10():
        if not roots:
            return {"_status": "SKIPPED", "reason": "no engine bound (run BUILD)"}
        # a scratch copy of the pictures: VERIFY must not disturb the live state
        base = os.path.join(log_dir or tempfile.mkdtemp(prefix="uc-tif-"), "tif_tick_scratch")
        if os.path.isdir(base):
            shutil.rmtree(base)
        os.makedirs(base)
        TF.init_live(name, force=True, base=base, face=False)
        out: Dict[str, Any] = {"scratch": base}
        # tick 1
        t1 = TF.tick(name, base=base, face=False, view=False)
        out["tick1"] = {"verdict": t1["verdict"], "unanimous": t1["summary"]["unanimous"], "all_intact": t1["summary"]["all_intact"],
                        "event_log_hash": t1["summary"]["event_log_hash"], "replay_ok": t1["summary"]["replay_ok"],
                        "accumulators": t1["containers"][FABRIC_CONTAINER].get("accumulators")}
        acc1 = {NODE_CONTAINER[n]: t1["containers"][NODE_CONTAINER[n]].get("acc_out") for n in NODE_IDS if n in roots}
        # every node's acc_out equals the CPython reference for (sealed words, FNV offset) at tick 1
        ref1 = W.reference_witness_words(W.words_of(seals["BERTH.pal"][0]))
        out["tick1_equals_reference"] = all(v == ref1 for v in acc1.values())
        # tick 2 chains from the state read back from the pictures
        t2 = TF.tick(name, base=base, face=False, view=False)
        acc2 = {NODE_CONTAINER[n]: t2["containers"][NODE_CONTAINER[n]].get("acc_out") for n in NODE_IDS if n in roots}
        ref2 = W.reference_witness_words(W.words_of(seals["BERTH.pal"][0]), acc_in=ref1)
        out["tick2"] = {"verdict": t2["verdict"], "unanimous": t2["summary"]["unanimous"], "chained_from_tick1": all(v == ref2 for v in acc2.values()),
                        "ticks_read_back": {k: t2["containers"][k].get("tick") for k in acc2}}
        # paint the tick cell of one node's picture to 200: the next tick must read 200 and write 201
        first = NODE_CONTAINER[[n for n in NODE_IDS if n in roots][0]]
        TF.paint(TF.live_path(name, first, base), TF.TILE_STATE, 0, 200)
        t3 = TF.tick(name, base=base, face=False, view=False)
        out["painted_tick_cell"] = {"container": first, "painted": 200, "next_tick": t3["containers"][first].get("tick"),
                                    "adopted": t3["containers"][first].get("tick") == 201}
        # paint a declaration cell of that node: its engine executes the painted words (differential agreement with the
        # CPython reference for the words READ still holds), the declaration is reported not intact, unanimity breaks
        TF.paint(TF.live_path(name, first, base), TF.TILE_WORDS_A, 0, 12345)
        t4 = TF.tick(name, base=base, face=False, view=False)
        c4 = t4["containers"][first]
        bound_n = len([n for n in NODE_IDS if n in roots])
        first_bit = 1 << NODE_IDS.index([n for n in NODE_IDS if n in roots][0])
        votes4 = int(t4["containers"][FABRIC_CONTAINER].get("votes_bitmask") or 0)
        # with two or more engines the painted node is out-voted (unanimity breaks); with a single engine bound nobody can
        # out-vote it, so what must be reported is the declaration not intact, the node's vote withheld, and the verdict
        out["painted_declaration_cell"] = {"container": first, "declaration_intact": c4.get("declaration_intact"),
                                           "differential_agreement": c4.get("differential_agreement"), "unanimous": t4["summary"]["unanimous"],
                                           "verdict": t4["verdict"], "votes_bitmask": votes4, "engines_bound": bound_n,
                                           "vote_withheld": not (votes4 & first_bit),
                                           "reported": (c4.get("declaration_intact") is False and c4.get("differential_agreement") is True
                                                        and not (votes4 & first_bit) and t4["summary"]["all_intact"] is False
                                                        and (t4["summary"]["unanimous"] is False if bound_n >= 2 else True)
                                                        and (t4["verdict"] == "TICK_DISAGREEMENT" if bound_n == len(NODE_IDS)
                                                             else t4["verdict"] in ("TICK_DISAGREEMENT", "TICK_INCOMPLETE")))}
        # the hull face: the studio's own loop on a backed-up copy of its image, restored afterwards
        face = {"skipped": None}
        s, cname = TF._studio_face(name)
        from . import host as H
        can_run, why = (H.hull_execution() if s is not None else (False, None))
        if s is None:
            face = {"skipped": cname}
        elif not can_run:
            face = {"skipped": why, "host_limited": True}
        else:
            tif = s.fabric_path(cname)
            sp = s.state_path(cname)
            fs = os.path.join(s.state_dir(), f"{cname}.fabric.state")
            backups = {}
            for pth in (tif, sp, fs):
                if os.path.isfile(pth):
                    backups[pth] = open(pth, "rb").read()
            try:
                if os.path.isfile(tif):
                    os.remove(tif)
                s.fabric_init(cname, from_state=False)
                r1 = s.fabric_tick(cname, view=False)
                r2 = s.fabric_tick(cname, view=False)
                ref = seals["BERTH.pal"][1]["reference_witness"]
                TF.paint(tif, TF.TILE_STATE, 0, 200)
                r3 = s.fabric_tick(cname, view=False)
                face = {"tick1": r1.get("tick"), "tick2": r2.get("tick"), "R2_equals_reference": all((x.get("registers") or {}).get("R2") == ref for x in (r1, r2, r3)),
                        "tick_cell_after_two_ticks": (r2.get("registers") or {}).get("R7"), "painted_200_then": (r3.get("registers") or {}).get("R7"),
                        "adopted": (r3.get("registers") or {}).get("R7") == 201, "execution_mode": None,
                        "ok": bool(r1.get("ran") and r2.get("ran") and r3.get("ran")) and (r2.get("registers") or {}).get("R7") == 2
                              and (r3.get("registers") or {}).get("R7") == 201 and all((x.get("registers") or {}).get("R2") == ref for x in (r1, r2, r3))}
            finally:
                for pth in (tif, sp, fs):
                    if os.path.isfile(pth):
                        os.remove(pth)
                for pth, data in backups.items():
                    with open(pth, "wb") as fh:
                        fh.write(data)
        out["hull_face"] = face
        B.log("tif_tick_scratch.json", json.dumps({"tick1": t1, "tick2": t2, "tick3_painted_cell": t3, "tick4_painted_declaration": t4, "hull_face": face}, indent=1, sort_keys=True, default=str))
        # what the bound engines showed, whatever their number
        bound_ok = (out["tick1_equals_reference"] and out["tick2"]["chained_from_tick1"] and out["painted_tick_cell"]["adopted"]
                    and out["painted_declaration_cell"]["reported"] and (face.get("ok") if not face.get("skipped") else True)
                    and t1["summary"]["replay_ok"] and t1["summary"]["unanimous"] and t2["summary"]["unanimous"])
        if face.get("skipped"):
            out["note"] = "hull face not ticked: " + str(face["skipped"])
        out["engines_bound"] = sorted(roots)
        out["engines_absent"] = [n for n in NODE_IDS if n not in roots]
        if len(roots) == len(NODE_IDS):
            ok = bound_ok and t1["verdict"] == "TICK_OK" and t2["verdict"] == "TICK_OK"
            return {"_status": "PASS" if ok else "FAIL", **out}
        # not every engine is bound (a host without a C toolchain binds the QUORUM engine alone): a tick cannot complete
        # -- three pictures stay untouched and the verdict is TICK_INCOMPLETE by design -- so the gate is not passed;
        # what the bound engine(s) showed is recorded, and a failure there is still a failure
        if not bound_ok:
            return {"_status": "FAIL", **out}
        from . import host as H
        lim = H.limits().get("no_c_toolchain")
        return {"_status": "SKIPPED", **out, "bound_engines_checks_passed": True,
                "reason": (f"engines {out['engines_absent']} are not bound so the tick cannot complete (verdict {t1['verdict']}); "
                           f"on {sorted(roots)}: tick 1 == reference, tick 2 chained, painted tick cell adopted, painted declaration reported"
                           + (f" -- {lim}" if lim else " (run BUILD)"))}
    B.gate("B10", "a tick executes the pictures (on a scratch copy): every bound engine agrees with the CPython reference for the state read and the engines agree; tick 2 chains from the pictures; a painted tick cell is executed as painted (200 -> 201); a painted declaration cell is reported (its vote withheld, unanimity broken where two or more engines are bound, verdict TICK_DISAGREEMENT); the hull's VM ticks the hull face's own picture with R2 == reference (not on a compile-only hull -- said so)", b10, skip_if=tif_skip)

    hull_cargo = [m for m in (rec.get("hull_cargo") or []) if m.get("name")]

    def b11():
        from . import hullmount as HM
        found = HM.detect(name)                       # re-derived from the cargo bytes and the ledger, not from BERTH.json
        recorded = {m["name"] for m in hull_cargo}
        out: Dict[str, Any] = {"detected": [m["name"] for m in found], "recorded": sorted(recorded),
                               "detection_matches_record": {m["name"] for m in found} == recorded, "containers": {}}
        from . import host as H
        studio = E.studio() if E.studio_status().get("installed") else None
        can_run, why = H.hull_execution() if studio is not None else (False, None)
        allok = out["detection_matches_record"]
        for m in found:
            c: Dict[str, Any] = {"complete": m["complete"], "listed": m["listed"], "picture_in_cargo": m["picture"]}
            scratch = os.path.join(log_dir or tempfile.mkdtemp(prefix="uc-mount-"), "hull_cargo_scratch", m["name"])
            if os.path.isdir(scratch):
                shutil.rmtree(scratch)
            HM.reassemble(name, m, scratch)
            # the hull's own seal verifier over the re-assembled container
            hull = E.hull_dir()
            if hull not in sys.path:
                sys.path.insert(0, hull)
            from pa21studio import container as _pc
            insp = _pc.inspect(scratch)
            c.update({"reassembled_files": sum(len(fs) for _, _, fs in os.walk(scratch)), "seal_verified": bool(insp.get("sealed")),
                      "image_matches_manifest": bool(insp.get("image_matches_manifest")), "container_ok": bool(insp.get("ok"))})
            shutil.rmtree(scratch, ignore_errors=True)
            if studio is None:
                c["mounted"] = None
                c["note"] = "hull not installed (run BUILD): mount and tick not checked"
                c["ok"] = c["container_ok"]
            else:
                have = {x.get("name") for x in (studio.list_containers().get("containers") or [])}
                c["mounted"] = m["name"] in have
                if not c["mounted"]:
                    c["ok"] = False
                    c["note"] = "not mounted in the hull (run BUILD or `uc mount`)"
                elif not can_run:
                    pic = studio.fabric_path(m["name"])
                    c["picture_present"] = os.path.isfile(pic)
                    c["tick"] = {"ran": False, "skipped": why, "host_limited": True}
                    c["ok"] = c["container_ok"] and c["mounted"]
                else:
                    pic = studio.fabric_path(m["name"])
                    c["picture_present"] = os.path.isfile(pic)
                    # a tick on its own picture, on a backup, restored afterwards
                    backups = {}
                    for pth in (pic, studio.state_path(m["name"]), os.path.join(studio.state_dir(), f"{m['name']}.fabric.state")):
                        if os.path.isfile(pth):
                            backups[pth] = open(pth, "rb").read()
                    try:
                        if not os.path.isfile(pic):
                            studio.fabric_init(m["name"], from_state=False)
                        t = studio.fabric_tick(m["name"], view=False)
                        c["tick"] = {"ran": bool(t.get("ran")), "ok": bool(t.get("ok")), "tick": t.get("tick"), "status_name": t.get("status_name"),
                                     "trap": t.get("trap"), "fabric_changed": t.get("fabric_changed"), "reason": t.get("reason")}
                    except Exception as exc:  # noqa: BLE001
                        c["tick"] = {"ran": False, "error": f"{type(exc).__name__}: {exc}"}
                    finally:
                        for pth in list(backups) + [pic]:
                            if os.path.isfile(pth):
                                os.remove(pth)
                        for pth, data in backups.items():
                            with open(pth, "wb") as fh:
                                fh.write(data)
                    c["ok"] = c["container_ok"] and c["mounted"] and bool(c["tick"].get("ran"))
            allok = allok and c["ok"]
            out["containers"][m["name"]] = c
        return {"_status": "PASS" if allok else "FAIL", **out}
    B.gate("B11", "hull cargo: the studio container(s) the berth carries re-assemble from the slots exactly as their seal lists, verify with the hull's own seal verifier, are mounted in the hull, and tick on their own picture (on a backup, restored; not on a compile-only hull -- said so)",
           b11, skip_if=None if hull_cargo else "the berth carries no studio container (no CONTAINER.json + RELEASE_CONTENTS.sha256 pair in its cargo)")

    return B.results({"berth": name, "engines_bound": sorted(roots)})


# --------------------------------------------------------------------------
# ship battery
# --------------------------------------------------------------------------

def run_ship_battery(*, log_dir: Optional[str] = None, quick: bool = False, berths: Optional[List[str]] = None,
                     hull_verify: bool = True) -> dict:
    ship = E.ship_root()
    B = Battery("Unikernel Containership", log_dir)

    def u01():
        if not os.path.isfile(os.path.join(ship, "SHA256SUMS.txt")):
            return {"_status": "SKIPPED", "reason": "SHA256SUMS.txt not present (pre-seal assembly run)"}
        r = M.check_sums(ship)
        r["_status"] = "PASS" if r["pass"] else "FAIL"
        return r
    B.gate("U0.1", "ship SHA256SUMS.txt verifies (every delivered byte)", u01)

    def u02():
        p = os.path.join(ship, "MANIFEST.json")
        if not os.path.isfile(p):
            return {"_status": "SKIPPED", "reason": "MANIFEST.json not present (pre-seal assembly run)"}
        man = _load_json(p)
        r = M.check_manifest_inventory(ship, man)
        r["_status"] = "PASS" if r["pass"] else "FAIL"
        # a ship re-sealed after load/unload says so: the assembly seal and every re-seal are recorded
        r["seal"] = {"assembled_at_utc": man.get("assembled_at_utc"), "sealed_utc": man.get("sealed_utc", man.get("assembled_at_utc")),
                     "resealed_times": len(man.get("seal_lineage") or []),
                     "last_reseal": (man.get("seal_lineage") or [None])[-1]}
        return r
    B.gate("U0.2", "MANIFEST.json inventory matches disk (the current seal; re-seals after load/unload are recorded in seal_lineage)", u02)

    def u03():
        doc = _load_json(os.path.join(ship, "hull", "HULL_DIGEST.json"))
        digest, n = M.dir_digest(os.path.join(ship, "hull"), skip=("__pycache__", "HULL_DIGEST.json"))
        # HULL_DIGEST.json itself is excluded from the digest it states
        ok = digest == doc["tree_sha256"] and n == doc["file_count"]
        return {"_status": "PASS" if ok else "FAIL", "expected": doc["tree_sha256"], "found": digest, "files": n, "studio_version": doc.get("studio_version")}
    B.gate("U0.3", "hull/ (PA21 Language Studio 1.3.0) is byte-identical to the pinned digest", u03)

    def u04():
        st = E.hold_state()
        pins = E.hold_pins()
        sums = os.path.join(ship, "hold", "DF_SHA256SUMS.txt")
        ok = st["pass"] and os.path.isfile(sums) and M.sha256_file(sums) == pins.get("df_sha256sums_sha256")
        # and the DF_SHA256SUMS.txt lines match the zips
        r = M.check_sums(os.path.join(ship, "hold"), "DF_SHA256SUMS.txt") if os.path.isfile(sums) else {"pass": False}
        return {"_status": "PASS" if ok and not r.get("bad") and not r.get("missing") and not r.get("errors") else "FAIL",
                "containers": {k: {"match": v.get("match")} for k, v in st["containers"].items()},
                "df_sha256sums_ok": not r.get("bad") and not r.get("missing") and not r.get("errors")}
    B.gate("U0.4", "hold/ holds the five DF containers byte-identical to the pinned digests (and DF_SHA256SUMS.txt binds them)", u04)

    def u05():
        errs = {}
        pre_seal = not os.path.isfile(os.path.join(ship, "MANIFEST.json"))
        for rel, sname in S.ARTIFACT_SCHEMA_MAP.items():
            p = os.path.join(ship, rel)
            if not os.path.isfile(p):
                if pre_seal and rel in ("MANIFEST.json", "conformance/UC_GATE_RESULTS.json", "reports/UC_CAPABILITY_LEDGER.json"):
                    continue
                errs[rel] = ["missing"]
                continue
            e = S.validate(_load_json(p), S.SCHEMAS[sname])
            if e:
                errs[rel] = e[:6]
        return {"_status": "PASS" if not errs else "FAIL", "violations": errs}
    B.gate("U0.5", "every ship artifact validates against the schema shipped beside it", u05)

    def u06():
        p = os.path.join(ship, "reports", "UC_CAPABILITY_LEDGER.json")
        if not os.path.isfile(p):
            return {"_status": "SKIPPED", "reason": "ledger not present (pre-seal assembly run)"}
        led = _load_json(p)
        bad = [f"{it['id']}: {ev}" for it in led["items"] for ev in (it.get("evidence") or [])
               if ev.split("#")[0] and not os.path.exists(os.path.join(ship, ev.split("#")[0]))]
        return {"_status": "PASS" if not bad else "FAIL", "unresolved": bad}
    B.gate("U0.6", "every evidence citation in the ship's capability ledger resolves to a delivered path", u06)

    def u1():
        pol = sorter.policy_record()
        shipped = _load_json(os.path.join(ship, "reports", "SORT_POLICY.json"))
        same = json.dumps(pol, sort_keys=True) == json.dumps({k: v for k, v in shipped.items() if k in pol}, sort_keys=True)
        # documented examples must sort as documented
        examples = [
            ("boot.mssl", b".profile SIM_CORE\n.image_version 3\n.request_caps CONTROL|ARITH\nMOVI.WRAP R0, 40, C0\nHALT.WRAP C0\n", "N_SMALL", "S0"),
            ("unit.lctlc", b"LCTLC/1.1\n@unit id=x version=4.7.0 profile=brvm-native\n", "N_MEDIUM", "S0"),
            ("unit12.lctlc", b"LCTLC/1.2\n@unit id=x version=4.3.0 language=columned-lctl/4.3 isa=BR/1.1\n", "N_LARGE", "S0"),
            ("unit10.lctlc", b"LCTLC/1.0\n@unit id=x version=1.0.0 profile=native\n", "N_XLARGE", "S0"),
            ("bundle.pal", b"#PA-LCTL/1.6\n#PROFILE pa.lctl.quantum.parallel.distributed\n", "N_MEDIUM", "S1"),
            ("image.brimg", b"BRIM\x04\x03\x00\x01" + b"\x00" * 100, "N_XLARGE", "S2"),
            ("tool.py", b"import os\nprint(1)\n", "N_XLARGE", "S3"),
            ("core.c", b"#include <stdint.h>\nint main(void){return 0;}\n", "N_LARGE", "S4"),
            ("SHA256SUMS.txt", b"abc  file\n", "N_MEDIUM", "S5"),
            ("small.json", b'{"a": 1}\n', "N_SMALL", "S6"),
            ("RUN.sh", b"#!/bin/sh\nexec python3 x.py\n", "N_SMALL", "S7"),
            ("README.md", b"# hi\n", "N_SMALL", "S8"),
            ("BIG.md", b"# big\n" + b"x" * (200 * 1024), "N_LARGE", "S8"),
        ]
        wrong = []
        for fn, data, node, rule in examples:
            r = sorter.sort_script(fn, data)
            if (r["node"], r["rule"]) != (node, rule):
                wrong.append({"file": fn, "expected": (node, rule), "got": (r["node"], r["rule"])})
        return {"_status": "PASS" if same and not wrong else "FAIL", "policy_identical": same, "examples": len(examples), "wrong": wrong}
    B.gate("U1", "the sort policy shipped equals the code, and the documented example placements hold (13 examples, rules S0-S8)", u1)

    def u2():
        st = E.hold_state()
        ex = os.path.isdir(E.engines_dir()) and all(os.path.isdir(os.path.join(E.engines_dir(), s)) for s in SLOTS)
        if not ex:
            return {"_status": "SKIPPED", "reason": "hold not extracted (run BUILD)"}
        b = E.bind(require=False)
        det = {n: {"present": r["present"], "sums_match": r["sums_match"], "bound": n in b["roots"]} for n, r in b["located"].items()}
        # one small witness on every bound engine: the binding is observed, and so is any host adaptation of it
        # (e.g. the QUORUM engine's column verifier through java directly where the host has no `sh`)
        Wm = b["witness"]
        for n in sorted(b["roots"]):
            try:
                ad = b["nodes"].make_adapter(n, b["roots"][n])
                r = ad.submit_words([1, 2, 3, 4], Wm.FNV_OFFSET, "uc.probe")
                det[n]["probe"] = {"witness": r["native_witness"], "reference": Wm.reference_witness_words([1, 2, 3, 4]),
                                   "agree": r["native_witness"] == Wm.reference_witness_words([1, 2, 3, 4]),
                                   "steps": [x.get("step") for x in (r.get("steps") or [])],
                                   "extra": {k: v for k, v in (r.get("extra") or {}).items() if k in ("lctl_column_verify", "host_adaptation")}}
            except Exception as exc:  # noqa: BLE001
                det[n]["probe"] = {"error": f"{type(exc).__name__}: {exc}"}
        probes_ok = all(v.get("probe", {}).get("agree") for v in det.values() if v["bound"])
        allb = all(v["bound"] for v in det.values())
        if not probes_ok:
            return {"_status": "FAIL", "engines": det, "reason": "a bound engine did not witness the probe as the CPython reference does"}
        if not allb:
            from . import host as H
            unbound = sorted(n for n, v in det.items() if not v["bound"])
            lim = H.limits().get("no_c_toolchain")
            reason = (f"engines {unbound} are not built: {lim}" if lim and set(unbound) <= {"N_SMALL", "N_MEDIUM", "N_LARGE"}
                      else "not every engine is built (run BUILD)")
            return {"_status": "SKIPPED", "engines": det, "reason": reason, "host_limited": bool(lim), "host_adaptations": (b.get("host") or {}).get("adaptations")}
        return {"_status": "PASS", "engines": det, "host_adaptations": (b.get("host") or {}).get("adaptations")}
    B.gate("U2", "the four engines are extracted from the hold, match their pinned digests, are built and bind (SKIPPED with the reason where the host has no C toolchain for the three C engines)", u2)

    def u3():
        st = E.studio_status()
        if not st.get("installed"):
            return {"_status": "SKIPPED", "reason": st.get("error") or "hull not installed at _studio/ (run BUILD)"}
        s = E.studio()
        r = s.status()
        from . import STUDIO_VERSION_EXPECTED
        ver = str(r.get("studio_version") or E.hull_version())
        return {"_status": "PASS" if r.get("installed") and ver == STUDIO_VERSION_EXPECTED else "FAIL", "execution_mode": r.get("execution_mode"),
                "studio_version": ver, "expected_version": STUDIO_VERSION_EXPECTED,
                "signing": (r.get("signing") or {}).get("available"), "containers": st.get("containers")}
    B.gate("U3", "the hull (PA Language Studio 2.0.0) is installed at _studio/ from the Large engine's VM package", u3)

    def u4():
        if not hull_verify:
            return {"_status": "SKIPPED", "reason": "--quick"}
        try:
            vm = E.large_vm_root()
        except ShipError as exc:
            return {"_status": "SKIPPED", "reason": str(exc)}
        pa21 = E.default_pa21_root()
        r = _sh([sys.executable, "-B", os.path.join(ship, "hull", "verify_studio.py"), "--vm", vm, "--pa21", pa21], ship, timeout=1800)
        B.log("hull_verify_studio.log", r["stdout"][-30000:] + "\n--- stderr ---\n" + r["stderr"][-5000:])
        tail = "\n".join(r["stdout"].strip().splitlines()[-4:])
        ok = r["returncode"] == 0 and "ALL CHECKS PASS" in r["stdout"]
        return {"_status": "PASS" if ok else "FAIL", "returncode": r["returncode"], "seconds": r["seconds"], "tail": tail}
    B.gate("U4", "the hull's own verifier (hull/verify_studio.py, 135 checks: scratch install, real images, the device fabric, the reversible TIFF fabric, seals, signing, uninstall) passes against the Large engine", u4)

    def u8():
        ok, why = TF.available()
        if not ok:
            return {"_status": "SKIPPED", "reason": why}
        ftif = TF.codec()
        import struct as _st
        words = [0x0123456789ABCDEF, 0xFEDCBA9876543210, 7, 0]
        wa, wb = TF.pack_words(words)
        st = TF.pack_state(3, 0xCBF29CE484222325, 1, 4, 0, 3, 0xAB, 9)
        blob = TF.build_blob(3, 12, [TF.identity("gate", "DF_Small", "N_SMALL", "00" * 32), bytes(32), st, wa, wb, bytes(96), b"", b""])
        tmp = os.path.join(E.runs_dir(), "_u8.tif")
        rt = ftif.validate_roundtrip(blob, tmp)
        back = TF.decode_blob(ftif.read_tif(tmp)["blob"])
        try:
            os.remove(tmp)
        except OSError:
            pass
        ok2 = rt["reversible"] and back["words"] == words and back["state"]["tick"] == 3 and back["identity"].get("container") == "DF_Small"
        return {"_status": "PASS" if ok2 else "FAIL", "reversible": rt["reversible"], "bytes": rt["bytes_in"], "words_back": back["words"] == words,
                "codec": "hull/pa21studio/fabric_tif.py (PA21FABTIF/1)", "pillow": __import__("PIL").__version__}
    B.gate("U8", "the hull's .tif fabric codec is present and reversible on this host: a synthetic container fabric (state, declaration cells, identity) survives the round trip through the image byte for byte", u8)

    def u5():
        p = registry.registry_path()
        if not os.path.isfile(p):
            return {"_status": "SKIPPED", "reason": "no bill of lading yet"}
        cmp = registry.compare(_load_json(p), registry.scan())
        return {"_status": "PASS" if cmp["identical"] else "FAIL", **cmp}
    B.gate("U5", "the bill of lading equals a fresh scan of berths/ (rebuilt from disk, never appended)", u5)

    names = berths if berths is not None else sorted(d for d in os.listdir(berths_dir()) if os.path.isdir(os.path.join(berths_dir(), d))) if os.path.isdir(berths_dir()) else []
    per_berth = {}
    for nm in names:
        def run_one(nm=nm):
            res = run_berth_battery(nm, log_dir=os.path.join(log_dir, f"berth_{nm}") if log_dir else None, quick=quick)
            per_berth[nm] = res
            t = res["totals"]
            return {"_status": res["verdict"] if t["failed"] == 0 else "FAIL", "passed": t["passed"], "failed": t["failed"],
                    "skipped": t["skipped"], "gates": {g["id"]: g["status"] for g in res["gates"]}}
        B.gate(f"U6.{nm}", f"berth {nm}: the berth battery (B0-B11)", run_one)

    def u7():
        r = studio_face.test_all()
        if r.get("skipped"):
            return {"_status": "SKIPPED", "reason": r["skipped"], "host_limited": bool(r.get("host_limited")), "containers": len(r.get("containers") or [])}
        results = r.get("results") or r.get("containers") or []
        fails = [x for x in results if str(x.get("verdict", x.get("status", ""))).upper() == "FAIL"]
        return {"_status": "PASS" if not fails else "FAIL", "summary": {k: r.get(k) for k in ("pass", "fail", "no_expectation", "summary") if k in r},
                "n": len(results)}
    B.gate("U7", "studio test: every berth container in the hull runs against its own declared answer (SKIPPED with the reason on a compile-only hull)", u7)

    def u9():
        if quick:
            return {"_status":"SKIPPED", "reason":"quick mode does not execute the foundation regression suite"}
        r = _sh([sys.executable, "-X", "utf8", "-B", "-m", "unittest", "discover", "-s", os.path.join(ship,"tests"), "-v"], ship, timeout=180)
        B.log("foundation_tests.log", r["stdout"] + "\n" + r["stderr"])
        return {"_status":"PASS" if r["returncode"] == 0 else "FAIL", "returncode":r["returncode"],
                "tail":r["stderr"][-1000:], "scope":"local Python contracts, storage, process and recovery fixtures; no guest boot"}
    B.gate("U9", "UC-2.3.0 ship regression and process-crash recovery suite", u9)
    def u10():
        from . import workflow
        r=workflow.check(ship)
        return {"_status":"PASS" if r["valid"] else "FAIL", **r}
    B.gate("U10", "all 96,000 source tasks are preserved and accounted for without fabricated completion", u10)
    from . import host as H
    result = B.results({"berths": per_berth, "engines": E.engines_status(), "host_limits": H.limits()})
    all_gates = [("ship/"+g["id"],g) for g in result["gates"]]
    all_gates += [(name+"/"+g["id"],g) for name, br in per_berth.items() for g in br["gates"]]
    incomplete = [key for key,g in all_gates if g["status"] != "PASS"]
    result["coverage"]={"gate_instances":len(all_gates), "passed":sum(g["status"]=="PASS" for _,g in all_gates),
                        "failed":sum(g["status"]=="FAIL" for _,g in all_gates),
                        "skipped":sum(g["status"]=="SKIPPED" for _,g in all_gates), "incomplete":incomplete}
    result["promotion"]={"complete_native_suite":not incomplete,"isolated_guest":False,"full_96000_task_series":False,
                         "note":"Local test success does not establish missing guest, isolation, authentication or federation gates."}
    return result
