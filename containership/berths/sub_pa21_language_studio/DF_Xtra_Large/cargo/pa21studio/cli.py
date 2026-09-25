"""The command line: the same surface as the Python API, for scripts that are
not written in Python.

Every command accepts `--json` and prints one JSON object on stdout when it is
given, so the studio can be driven from PowerShell, a Makefile, CI, or another
language without parsing prose. Exit codes are the contract:

    0  the thing asked for happened
    1  it did not, and the JSON says why
    2  the request itself was malformed
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

from .core import Studio, StudioError, VERSION
from . import container as containers
from . import lctlc, ledger as pa21_ledger, probe as probe_mod

BULLET = "  "


def _print(obj: Dict[str, object], as_json: bool, lines: Optional[List[str]] = None):
    if as_json:
        print(json.dumps(obj, indent=2, sort_keys=True, default=str))
    else:
        for line in lines or []:
            print(line)


def _progress(ev: Dict[str, object]) -> None:
    pct = ev.get("progress")
    bar = f"[{int(float(pct) * 100):3d}%] " if isinstance(pct, (int, float)) else ""
    mark = "" if ev.get("ok", True) else "!! "
    msg = ev.get("message") or ev.get("phase") or ""
    sys.stderr.write(f"{bar}{mark}{ev.get('phase', '')}: {msg}\n")
    sys.stderr.flush()


def cmd_status(a) -> int:
    s = Studio(a.root)
    st = s.status(deep=a.deep)
    caps = st["capabilities"]
    lines = [
        f"PA21 Language Studio {VERSION}",
        f"{BULLET}root            {st['root']}",
        f"{BULLET}installed       {st['installed']}"
        + (f"  ({st.get('installed_utc')})" if st["installed"] else ""),
    ]
    if st["installed"]:
        rt = st.get("runtime", {})
        lines += [f"{BULLET}runtime         {rt.get('name')}",
                  f"{BULLET}execution       {st.get('execution_mode')}"]
        p = st.get("pa21", {})
        if p.get("found"):
            lines.append(f"{BULLET}PA21            {p.get('round')}  "
                         f"{p.get('operational')}/{p.get('items')} operational  "
                         f"({p.get('package_count')} packages)")
        else:
            lines.append(f"{BULLET}PA21            not bound")
        lines.append(f"{BULLET}applications    {len(st.get('apps', []))}")
    if st["installed"]:
        lines.append(f"{BULLET}fabric backend  {st.get('fabric_backend')}")
    if st["installed"]:
        sg = st.get("signing") or {}
        lines.append(f"{BULLET}signing         "
                     + ("images are signed at build and verified before they "
                        "run" if sg.get("available") and sg.get("runner_verifies")
                        else str(sg.get("reason") or "not available")))
    lines += [
        f"{BULLET}compile images  {caps['compile_images']}",
        f"{BULLET}execute images  {caps['execute_images']}",
        f"{BULLET}sign images     {caps['build_signing_cli']}",
    ]
    for name, f in st["findings"].items():
        if not f["available"] and f.get("remedy"):
            lines.append(f"{BULLET}{name}: {f['detail']} — {f['remedy']}")
    _print(st, a.json, lines)
    return 0


def cmd_probe(a) -> int:
    pr = probe_mod.probe_all(refresh=True)
    lines = [f"{k}: {'yes' if v['available'] else 'no'} — {v['detail']}"
             for k, v in pr["findings"].items()]
    _print(pr, a.json, lines)
    return 0


def cmd_plan(a) -> int:
    s = Studio(a.root)
    plan = (s.plan_uninstall(purge=a.purge) if a.uninstall
            else s.plan_install(a.vm, a.pa21, build=not a.no_build))
    lines = ["plan"]
    for k in ("will_write", "will_remove"):
        for p in plan.get(k, []):
            lines.append(f"{BULLET}{k[5:]}: {p}")
    for n in plan.get("notes", []):
        lines.append(f"{BULLET}note: {n}")
    _print(plan, a.json, lines)
    return 0


def cmd_install(a) -> int:
    s = Studio(a.root)
    try:
        res = s.install(a.vm, a.pa21, build=not a.no_build, force=a.force,
                        on_event=None if a.quiet or a.json else _progress)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    lines = [f"installed at {res['root']}",
             f"{BULLET}runtime    {res['runtime']}",
             f"{BULLET}execution  {res['execution_mode']}",
             f"{BULLET}proof      {res['proof'].get('summary')}",
             f"{BULLET}seconds    {res['seconds']}"]
    _print(res, a.json, lines)
    return 0 if res["ok"] else 1


def cmd_uninstall(a) -> int:
    s = Studio(a.root)
    res = s.uninstall(purge=a.purge,
                      on_event=None if a.quiet or a.json else _progress)
    lines = [f"removed {len(res['removed'])} path(s) from {res['root']}"]
    if res.get("residue_count"):
        lines.append(f"{BULLET}{res['residue_count']} file(s) left alone: not "
                     f"created by this installation")
    for f in res.get("failed", []):
        lines.append(f"{BULLET}could not remove {f['path']}: {f['error']}")
    _print(res, a.json, lines)
    return 0 if res["ok"] else 1


def cmd_new(a) -> int:
    s = Studio(a.root)
    try:
        res = s.new_app(a.name, path=a.path, template=a.template,
                        requires_operational=[int(x) for x in a.requires],
                        version=a.app_version, source=a.source,
                        state=a.state,
                        mailbox_in=bytes.fromhex(a.mailbox_in)
                        if a.mailbox_in else None)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    _print(res, a.json, [f"created container {res['path']}",
                         f"{BULLET}entry     {res['entry']}",
                         f"{BULLET}manifest  {res['manifest']}",
                         f"{BULLET}state     {res['state']} "
                         f"({res['sealed_files']} files sealed)",
                         f"{BULLET}template  {res['template']}",
                         f"{BULLET}next      {res['next']}"])
    return 0


def cmd_templates(a) -> int:
    t = {"templates": lctlc.template_list()}
    _print(t, a.json, [f"{x['name']:<8} {x['title']:<18} {x['summary']}"
                       for x in t["templates"]])
    return 0


def cmd_build(a) -> int:
    s = Studio(a.root)
    try:
        res = s.build_app(a.app)
    except (StudioError, lctlc.ToolchainError) as e:
        _print({"ok": False, "error": str(e),
                "detail": getattr(e, "detail", {})}, a.json,
               [f"build failed: {e}"])
        return 1
    _print(res, a.json,
           [f"built {res['name']}",
            f"{BULLET}image      {res['image']}  ({res['image_bytes']} bytes)",
            f"{BULLET}sha256     {res['image_sha256']}",
            f"{BULLET}provenance {res['provenance']}",
            f"{BULLET}seconds    {res['seconds']}"])
    return 0


def _registers(regs: Dict[str, object]) -> str:
    """The registers that hold something, and a count of the ones that do not.

    All sixteen are in the JSON, because something reading it may be looking
    for a particular one. A person reading a line of output is looking for
    what changed.
    """
    live = [f"{k}={v}" for k, v in (regs or {}).items() if v]
    rest = len(regs or {}) - len(live)
    if not live:
        return f"all {rest} zero"
    return " ".join(live) + (f"  (+{rest} zero)" if rest else "")


def _repair_lines(res: Dict[str, object]) -> List[str]:
    """Every edit the studio made on the author's behalf, and none silently."""
    out = []
    for r in res.get("repairs") or []:
        out.append(f"{BULLET}fixed      {r['refusal']}")
        out.append(f"{BULLET}           {r['change']}")
    return out


def _quiet_lines(res: Dict[str, object]) -> List[str]:
    """Name the service calls that ran without leaving a trace."""
    eff = res.get("effects") or {}
    out = []
    for q in eff.get("quiet", []):
        out.append(f"{BULLET}quiet      {q['service']}: {q['why']}")
        out.append(f"{BULLET}           {q['do']}")
    return out


def cmd_run(a) -> int:
    s = Studio(a.root)
    try:
        res = s.run_app(a.app, budget=a.budget,
                        check_expectations=not a.no_check,
                        skip_gate=a.skip_gate, adapter=a.adapter,
                        seed=a.seed,
                        console_in=bytes.fromhex(a.console_in)
                        if a.console_in else None,
                        devices=True if a.devices else None,
                        build_if_stale=a.build, state=a.state,
                        signed=False if a.unsigned else None,
                        trace=(a.trace if a.trace is not None else None),
                        mailbox_in=bytes.fromhex(a.mailbox_in)
                        if a.mailbox_in else None)
    except (StudioError, lctlc.ToolchainError) as e:
        _print({"ok": False, "error": str(e),
                "detail": getattr(e, "detail", {})}, a.json, [f"refused: {e}"])
        return 1
    if not res.get("ran"):
        lines = [f"{res.get('state') or 'refused'}: {res.get('reason')}"]
        if res.get("note"):
            lines.append(f"{BULLET}{res['note']}")
        if res.get("hint"):
            lines.append(f"{BULLET}{res['hint']}")
        _print(res, a.json, lines)
        return 1
    fab = res.get("fabric") or {}
    lines = [f"{res['name']}: {res['status_name']} trap={res['trap']} "
             f"in {res['seconds']}s ({res['execution_mode']}, "
             f"{res.get('adapter')} backend in {res.get('backend')})",
             f"{BULLET}registers  " + _registers(res["registers"])]
    if fab:
        stored = [o for o in fab.get("storage", []) if o.get("framed_bytes")]
        lines.append(f"{BULLET}fabric     console {fab.get('console_out_bytes', 0)}"
                     f" byte(s)"
                     + (f" {fab.get('console_out_text')!r}"
                        if fab.get("console_out_bytes") else "")
                     + f", {len(stored)} storage object(s) written, "
                       f"monotonic {fab.get('monotonic')}")
    sig = res.get("signature") or {}
    if sig.get("not_verified_because"):
        lines.append(f"{BULLET}unverified {sig['not_verified_because']}")
    flt = res.get("fault") or {}
    if flt.get("trapped"):
        lines.append(f"{BULLET}trapped    {flt.get('summary')}")
        for d in (flt.get("diagnostics") or [])[-3:]:
            w = d.get("where") or {}
            if d.get("trap"):
                lines.append(f"{BULLET}           the VM logged {d['trap']} at "
                             f"row {w.get('row')} (line {w.get('line')})")
    for t in (flt.get("trace") or [])[-6:]:
        lines.append(f"{BULLET}trace      step {t.get('step')}: row "
                     f"{t.get('row')} {t.get('op')} — {t.get('text')}")
    st = res.get("fabric_state") or {}
    if st.get("mode") == "keep":
        carried = "yes" if st.get("carried_in") else "no (first run)"
        wrote = "yes" if st.get("written") else "no"
        lines.append(f"{BULLET}state      carried in {carried}, "
                     f"written {wrote}")
    if fab.get("mailbox_received_bytes"):
        lines.append(f"{BULLET}mailbox    the host received "
                     f"{fab['mailbox_received_bytes']} byte(s): "
                     f"{fab.get('mailbox_received_hex')}")
    lines += _quiet_lines(res)
    for c in res.get("expectation_checks", []):
        lines.append(f"{BULLET}{'ok ' if c['ok'] else 'NOT'} {c['field']}: "
                     f"expected {c['expected']}, got {c['actual']}")
    _print(res, a.json, lines)
    return 0 if res.get("ok") else 1


def cmd_verify(a) -> int:
    s = Studio(a.root)
    try:
        res = s.verify_app(a.app)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    _print(res, a.json,
           [f"{res['name']}: {'verified' if res['ok'] else 'NOT verified'}"] +
           [f"{BULLET}{'ok ' if c['ok'] else 'NOT'} {c['check']}: {c['detail']}"
            for c in res["checks"]])
    return 0 if res["ok"] else 1


def cmd_describe(a) -> int:
    s = Studio(a.root)
    d = s.describe()
    lang = d["language"]
    lines = [f"COLUMNED LCTL {lang['language']} on {lang['isa']} — "
             f"container format {d['container_format']}",
             f"{BULLET}columns   " + " │ ".join(lang["columns"]),
             f"{BULLET}separators columns {lang['column_separator_codepoint']}, "
             f"operands {lang['operand_separator_codepoint']}",
             f"{BULLET}unit      {lang['unit_line']}"]
    for r in lang["rules"]:
        lines.append(f"{BULLET}rule: {r['rule']}")
    if "services" in lang:
        lines.append(f"{BULLET}services  " +
                     ", ".join(f"{k}({v['capability']})"
                               for k, v in list(lang["services"].items())[:8])
                     + " …")
    lines.append(f"{BULLET}loop      " + " → ".join(
        x.split(" ")[1] for x in d["writing_loop"][:4]))
    lines.append("run with --json for the machine-readable contract")
    _print(d, a.json, lines)
    return 0


def cmd_try(a) -> int:
    s = Studio(a.root)
    if a.source == "-":
        text = sys.stdin.read()
    else:
        with open(os.path.abspath(os.path.expanduser(a.source)),
                  encoding="utf-8") as fh:
            text = fh.read()
    try:
        res = s.try_source(text, keep=a.keep,
                           requires_operational=[int(x) for x in a.requires],
                           adapter=a.adapter, budget=a.budget,
                           console_in=bytes.fromhex(a.console_in)
                           if a.console_in else None,
                           run=not a.no_run, fix=a.fix)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    if not res["compiled"]:
        h = res.get("hint") or {}
        lines = [f"did not compile: {res.get('error')}"]
        lines += _repair_lines(res)
        lines += [f"{BULLET}means  {h.get('means')}",
                  f"{BULLET}do     {h.get('do')}"]
        if res.get("repair_declined"):
            lines.append(f"{BULLET}not mine to fix: "
                         f"{res['repair_declined']['why']}")
        _print(res, a.json, lines)
        return 1
    lines = _repair_lines(res)
    lines += [f"compiled: {res['image_bytes']} bytes, "
              f"{res.get('instructions')} instructions",
              f"{BULLET}capabilities "
              f"{', '.join(res.get('capabilities') or [])}",
              f"{BULLET}devices      "
              f"{', '.join(res.get('devices') or []) or 'none'}"]
    if res.get("ran"):
        fab = res.get("fabric") or {}
        lines += [f"{BULLET}ran          {res['status_name']} "
                  f"trap={res['trap']} " +
                  _registers(res.get("registers") or {})]
        if fab.get("console_out_bytes"):
            lines.append(f"{BULLET}console      "
                         f"{fab['console_out_text']!r}")
        for name, ev in ((res.get("effects") or {}).get("observed") or
                         {}).items():
            lines.append(f"{BULLET}did          {name}: {ev}")
        lines += _quiet_lines(res)
    elif res.get("error"):
        lines.append(f"{BULLET}did not run  {res['error']}")
    if res.get("kept"):
        lines.append(f"{BULLET}kept as      {res['kept']}")
    _print(res, a.json, lines)
    return 0 if res.get("ok") else 1


def cmd_explain(a) -> int:
    from .describe import explain
    d = explain(" ".join(a.message))
    _print(d, a.json, [f"{'recognised' if d['recognised'] else 'unrecognised'}: "
                       f"{d['means']}", f"{BULLET}do  {d['do']}"])
    return 0


def cmd_trust(a) -> int:
    """Accept signatures from a key, or list the keys already accepted."""
    s = Studio(a.root)
    if not a.add:
        keys = s.trusted_keys()
        _print({"trusted": keys, "count": len(keys)}, a.json,
               [f"{d[:16]}  {p}" for d, p in keys.items()]
               or ["no keys are trusted by this studio"])
        return 0
    try:
        res = s.trust(a.add)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    _print(res, a.json, [f"trusting {res['key_sha256'][:16]}…",
                         f"{BULLET}from  {res['source']}",
                         f"{BULLET}{res['note']}"])
    return 0


def cmd_fabric(a) -> int:
    """The fabric as a picture you can run: init, tick, live, view, frames."""
    s = Studio(a.root)
    try:
        if a.action == "init":
            res = s.fabric_init(a.container, cols=a.cols)
            lines = [f"fabric image for {res['container']}: {res['fabric']}",
                     f"{BULLET}grid   {res['grid']['rows']}x{res['grid']['cols']} "
                     f"shards, {res['bytes']} byte .tif",
                     f"{BULLET}{res['note']}"]
        elif a.action == "tick":
            res = s.fabric_tick(a.container, adapter=a.adapter or
                                "deterministic",
                                mailbox_in=bytes.fromhex(a.mailbox_in)
                                if a.mailbox_in else None,
                                view=not a.no_view)
            if not res.get("ran"):
                _print(res, a.json, [f"refused: {res.get('reason')}"])
                return 1
            lines = [f"tick {res['tick']}: "
                     f"{'the fabric changed' if res['fabric_changed'] else 'still'}"
                     f"  ({res['pages']} frames on file)",
                     f"{BULLET}registers  " + _registers(res.get("registers") or {})]
            if res.get("view"):
                lines.append(f"{BULLET}view       {res['view']}")
        elif a.action == "live":
            def ev(e):
                mark = " " if e.get("ok", True) else "!"
                sys.stderr.write(f"{mark} {e.get('phase','')}: "
                                 f"{e.get('message','')}\n")
                sys.stderr.flush()
            res = s.fabric_live(a.container, ticks=a.ticks or 0,
                                interval=a.interval, adapter=a.adapter or
                                "deterministic",
                                on_event=None if a.json else ev,
                                stop_when_still=a.until_still)
            lines = [f"ran {res['ticks']} tick(s) of {res['container']}",
                     f"{BULLET}fabric  {res['fabric']}",
                     f"{BULLET}{res['note']}"]
        elif a.action == "view":
            res = s.fabric_view(a.container, out=a.out, scale=a.scale)
            lines = [f"rendered {res['container']}: {res['view']}",
                     f"{BULLET}{res['cells'][0]}x{res['cells'][1]} cells -> "
                     f"{res['pixels'][0]}x{res['pixels'][1]} px"]
        elif a.action == "frames":
            res = s.fabric_frames(a.container)
            lines = [f"{res['pages']} frame(s) of {res['container']}, newest first"]
            for f in res["frames"]:
                lines.append(f"{BULLET}page {f['page']}: tick {f['tick']}, "
                             f"monotonic {f['monotonic']}")
        else:
            _print({"ok": False, "error": "unknown fabric action"}, a.json,
                   ["actions: init, tick, live, view, frames"])
            return 2
    except (StudioError, Exception) as e:
        if isinstance(e, StudioError):
            _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
                   [f"refused: {e}"])
        else:
            _print({"ok": False, "error": str(e)}, a.json, [f"error: {e}"])
        return 1
    _print(res, a.json, lines)
    return 0


def cmd_doctor(a) -> int:
    """What this host can do, and what it merely ships."""
    s = Studio(a.root)
    res = s.doctor()
    p = res["platform"]
    lines = [f"{p['system']} {p['release']}, Python {p['python']}, "
             f"{p['compiler'] or 'no compiler'} ({p['compiler_kind']})"]
    for e in res["exercised"]:
        lines.append(f"{BULLET}{'ok ' if e['ok'] else 'NOT'} {e['check']}: "
                     f"{e['detail'][:90]}")
    for u in res["untested_here"]:
        lines.append(f"{BULLET}untested: {u}")
    lines.append(res["summary"])
    _print(res, a.json, lines)
    return 0 if res["ok"] else 1


def cmd_expect(a) -> int:
    """Record what a container does now as what it is expected to do."""
    s = Studio(a.root)
    try:
        res = s.capture_expectations(a.container, registers=a.registers or (),
                                     fabric_keys=a.fabric or (),
                                     write=not a.dry_run, state=a.state)
    except (StudioError, lctlc.ToolchainError) as e:
        _print({"ok": False, "error": str(e), "detail": getattr(e, "detail", {})},
               a.json, [f"refused: {e}"])
        return 1
    e = res["expect"]
    lines = [f"{res['container']}: {'recorded' if res['written'] else 'would record'} "
             f"{e['status_name']} trap={e['trap']}",
             f"{BULLET}registers  " + (" ".join(f"{k}={v}" for k, v in
                                                e["registers"].items())
                                       or "none"),
             f"{BULLET}fabric     " + (", ".join(f"{k}={v!r}" for k, v in
                                                 e["fabric"].items())
                                       or "none"),
             f"{BULLET}on         the deterministic adapter, so it is "
             f"reproducible"]
    if res["written"]:
        lines.append(f"{BULLET}sealed     {res['path']}")
    _print(res, a.json, lines)
    return 0


def cmd_test(a) -> int:
    """Run every container against what it declares it should do."""
    s = Studio(a.root)
    res = s.test_all(only=a.container or ())
    lines = []
    for r in res["results"]:
        lines.append(f"[{r['verdict']:<15}] {r['container']:<20} "
                     f"{r.get('detail', '')[:70]}")
    lines.append(res["summary"])
    _print(res, a.json, lines)
    return 0 if res["ok"] else 1


def cmd_abi(a) -> int:
    """Demonstrate the ABI the description claims, one program per claim."""
    s = Studio(a.root)
    try:
        res = s.abi_evidence(only=a.service)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    lines = []
    for c in res["claims"]:
        lines.append(f"[{c['verdict']:<8}] {c['service']:<14} {c['claim']}")
        lines.append(f"{BULLET}           "
                     f"{c.get('reason') or c['shows']}")
    lines.append(res["summary"])
    _print(res, a.json, lines)
    return 0 if res["ok"] else 1


def cmd_fix(a) -> int:
    """Apply the corrections that have one legal form, and say which."""
    s = Studio(a.root)
    path = None
    if a.source == "-":
        text = sys.stdin.read()
    else:
        path = os.path.abspath(os.path.expanduser(a.source))
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    try:
        res = s.fix_source(text)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    res["ok"] = bool(res.get("compiled"))
    lines = []
    for r in res.get("repairs") or []:
        lines.append(f"fixed: {r['refusal']}")
        lines.append(f"{BULLET}{r['change']}")
    if not res.get("repairs"):
        lines.append("nothing to fix" if res.get("compiled")
                     else f"nothing this studio may fix: {res.get('error')}")
    if res.get("compiled"):
        lines.append(f"{BULLET}the source compiles"
                     + (" (unchanged)" if not res.get("changed") else ""))
    else:
        lines.append(f"{BULLET}still refused: {res.get('error')}")
        if res.get("declined"):
            lines.append(f"{BULLET}not mine to fix: {res['declined']['why']}")
        else:
            lines.append(f"{BULLET}{res.get('reason')}")
    if a.write and res.get("changed"):
        if not path:
            lines.append(f"{BULLET}--write needs a file, not a pipe; the "
                         f"corrected source went to stdout instead")
        else:
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(str(res["source"]))
            res["written"] = path
            lines.append(f"{BULLET}wrote {path}")
    if a.json:
        _print(res, True)
        return 0 if res.get("compiled") else 1
    # the corrected source is the output of this command, so it goes to
    # stdout and the account of what changed goes to stderr -- which makes
    # `generator | studio fix - | studio try --from -` a pipeline
    if (path is None or not a.write) and res.get("changed"):
        sys.stdout.write(str(res["source"]))
    for line in lines:
        sys.stderr.write(line + "\n")
    return 0 if res.get("compiled") else 1


def cmd_watch(a) -> int:
    s = Studio(a.root)

    def ev(e):
        mark = " " if e.get("ok", True) else "!"
        sys.stderr.write(f"{mark} {e.get('phase','')}: {e.get('message','')}\n")
        sys.stderr.flush()

    try:
        res = s.watch(a.container, on_event=None if a.json else ev,
                      once=a.once, run=not a.no_run,
                      iterations=a.rounds or 0, fix=a.fix)
    except StudioError as e:
        _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
               [f"refused: {e}"])
        return 1
    _print(res, a.json, [f"{res['rounds']} build(s) while watching "
                         f"{res['name']}"])
    return 0


def cmd_containers(a) -> int:
    s = Studio(a.root)
    if a.install:
        try:
            res = s.import_container(a.install, force=a.force)
        except StudioError as e:
            _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
                   [f"refused: {e}"])
            return 1
        _print(res, a.json,
               [f"imported {res['name']} {res['version']} into {res['path']}",
                f"{BULLET}state    {res['state']}",
                f"{BULLET}devices  {', '.join(res['devices']) or 'none'}",
                f"{BULLET}gate     {res['gate'].get('reason')}"])
        return 0
    if a.state_reset:
        try:
            res = s.reset_state(a.state_reset)
        except StudioError as e:
            _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
                   [f"refused: {e}"])
            return 1
        _print(res, a.json,
               [f"{'discarded' if res['existed'] else 'no'} fabric state for "
                f"{res['container']}", f"{BULLET}{res['note']}"])
        return 0
    if a.remove:
        try:
            res = s.remove_container(a.remove)
        except StudioError as e:
            _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
                   [f"refused: {e}"])
            return 1
        _print(res, a.json, [f"removed {res['removed']}",
                             f"{BULLET}{res['remaining']} container(s) left"])
        return 0
    if a.pack:
        try:
            res = s.pack_container(a.pack, a.out)
        except StudioError as e:
            _print({"ok": False, "error": str(e), "detail": e.detail}, a.json,
                   [f"refused: {e}"])
            return 1
        _print(res, a.json,
               [f"packed {res['name']} {res['version']} -> {res['archive']}",
                f"{BULLET}bytes   {res['bytes']}",
                f"{BULLET}sha256  {res['sha256']}"])
        return 0
    res = s.list_containers(verify=a.verify)
    lines = [f"{res['count']} container(s) in {res['containers_dir']} "
             f"({res['format']})"]
    for c in res["containers"]:
        bits = [f"{c['name']:<20}", f"{str(c['version']):<8}",
                f"{c['state']:<12}"]
        if a.verify:
            # the label follows the state, not merely "does the seal match":
            # a container being written is not a container that has been
            # tampered with, and saying so is the difference between a tool
            # that reads as an author's and one that reads as an auditor's
            bits.append("sealed" if c.get("sealed") else
                        "edited since build" if c["state"] == "DRAFT" else
                        "not built yet" if c["state"] == "SOURCE_ONLY" else
                        "SEAL BROKEN")
            g = c.get("gate") or {}
            bits.append("gate ok" if g.get("satisfied") else "gate blocked")
        bits.append(", ".join(c["devices"]) or "no services")
        lines.append(f"{BULLET}" + "  ".join(bits))
    for c in res["containers"]:
        if c.get("next") and not c.get("sealed", True):
            lines.append(f"{BULLET}{'':<20}  next: {c['next']} {c['name']}")
    _print(res, a.json, lines)
    # a container being edited is not a failure; a broken seal is
    return 0 if all(c.get("healthy", True) for c in res["containers"]) else 1


def cmd_list(a) -> int:
    s = Studio(a.root)
    res = s.list_apps()
    _print(res, a.json,
           [f"{x['name']:<20} "
            f"{'container' if x.get('container') else 'legacy app':<12} "
            f"{x.get('state') or ('built' if x['built'] else 'source only'):<12} "
            f"{x['path']}" for x in res["apps"]] or ["nothing yet"])
    return 0


def cmd_selftest(a) -> int:
    s = Studio(a.root)
    res = s.selftest(deep=not a.quick)
    _print(res, a.json,
           [f"selftest: {res['summary']}"] +
           [f"{BULLET}{'ok ' if c['ok'] else 'NOT'} {c['check']}: {c['detail']}"
            for c in res["checks"]])
    return 0 if res["ok"] else 1


def cmd_ledger(a) -> int:
    root = a.pa21
    if not root:
        s = Studio(a.root)
        root = (s.manifest().get("pa21", {}) or {}).get("root") \
            if s.installed else None
    if not root:
        _print({"ok": False, "error": "no PA21 root given or bound"}, a.json,
               ["no PA21 root given or bound"])
        return 1
    sur = pa21_ledger.survey(os.path.abspath(os.path.expanduser(root)))
    lines = [f"PA21 delivery at {sur['root']}"]
    if sur.get("found"):
        lines += [f"{BULLET}round        {sur.get('round')}",
                  f"{BULLET}packages     {sur.get('package_count')}",
                  f"{BULLET}items        {sur.get('items')}",
                  f"{BULLET}distribution " +
                  " ".join(f"{k}={v}" for k, v in
                           sorted(sur.get("distribution", {}).items()))]
        if a.item:
            led = pa21_ledger.Ledger(sur["ledger_path"])
            for i in a.item:
                d = led.describe(int(i))
                lines.append(f"{BULLET}#{d['id']}: {d.get('status')} — "
                             f"{str(d.get('upgrade'))[:60]}")
            sur["queried"] = [led.describe(int(i)) for i in a.item]
    else:
        lines.append(f"{BULLET}{sur.get('reason')}")
    _print(sur, a.json, lines)
    return 0 if sur.get("found") else 1


def cmd_seal(a) -> int:
    root = os.path.abspath(os.path.expanduser(a.pa21))
    pkgs = pa21_ledger.find_packages(root)
    results = [pa21_ledger.verify_seal(p, limit=a.limit) for p in pkgs]
    out = {"root": root, "packages": results,
           "ok": all(r["sealed"] for r in results), "count": len(results)}
    _print(out, a.json,
           [f"{r['package']:<46} {'sealed' if r['sealed'] else 'NOT SEALED'} "
            f"({r['files_listed']} files)" for r in results])
    return 0 if out["ok"] else 1


def cmd_ui(a) -> int:
    from .ui_server import serve
    return serve(root=a.root, port=a.port, open_browser=not a.no_browser,
                 vm_default=a.vm, pa21_default=a.pa21)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="studio",
        description="PA21 Language Studio — install a COLUMNED LCTL runtime, "
                    "then build, verify and run applications against a "
                    "PA21.31 delivery.")
    p.add_argument("--root", help="studio root (default: %%LOCALAPPDATA%%\\"
                                  "PA21LanguageStudio or ~/.pa21-studio)")
    p.add_argument("--json", action="store_true", help="print one JSON object")
    p.add_argument("--version", action="version", version=f"studio {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("status", help="what is installed and what works")
    q.add_argument("--deep", action="store_true",
                   help="also run the selftest")
    q.set_defaults(f=cmd_status)

    q = sub.add_parser("probe", help="what this machine can do")
    q.set_defaults(f=cmd_probe)

    q = sub.add_parser("plan", help="what an install or uninstall would do")
    q.add_argument("--vm", help="VM package (.zip or directory)")
    q.add_argument("--pa21", help="PA21 delivery root")
    q.add_argument("--uninstall", action="store_true")
    q.add_argument("--purge", action="store_true")
    q.add_argument("--no-build", action="store_true")
    q.set_defaults(f=cmd_plan)

    q = sub.add_parser("install", help="install a runtime from a VM package")
    q.add_argument("--vm", required=True, help="VM package (.zip or directory)")
    q.add_argument("--pa21", help="PA21 delivery root to bind")
    q.add_argument("--no-build", action="store_true",
                   help="copy and verify only; do not build the runner")
    q.add_argument("--force", action="store_true", help="replace an existing "
                                                        "installation")
    q.add_argument("--quiet", action="store_true")
    q.set_defaults(f=cmd_install)

    q = sub.add_parser("uninstall", help="remove what this studio installed")
    q.add_argument("--purge", action="store_true",
                   help="also remove applications and anything else under the "
                        "root")
    q.add_argument("--quiet", action="store_true")
    q.set_defaults(f=cmd_uninstall)

    q = sub.add_parser("new", help="create a project: one sealed container")
    q.add_argument("name")
    q.add_argument("--path",
                   help="where to create it (default: <root>/containers)")
    q.add_argument("--app-version", default="0.1.0", dest="app_version",
                   help="the project's own version, recorded in CONTAINER.json")
    q.add_argument("--template", default="hello")
    q.add_argument("--requires", nargs="*", default=[],
                   help="PA21 ledger item ids this application requires to be "
                        "OPERATIONAL")
    q.add_argument("--from", dest="source", metavar="FILE",
                   help="build the container around code you already have; "
                        "'-' reads it from standard input")
    q.add_argument("--state", choices=("fresh", "keep"), default="fresh",
                   help="declare that this container's fabric carries over "
                        "between runs")
    q.add_argument("--mailbox-in", default=None, dest="mailbox_in",
                   help="hex bytes this container expects the host to have "
                        "waiting in the mailbox")
    q.set_defaults(f=cmd_new)

    q = sub.add_parser("templates", help="available application templates")
    q.set_defaults(f=cmd_templates)

    q = sub.add_parser("build", help="compile an application to an image")
    q.add_argument("app")
    q.set_defaults(f=cmd_build)

    q = sub.add_parser("run", help="execute an application on the runtime")
    q.add_argument("app")
    q.add_argument("--budget", type=int, help="instruction budget")
    q.add_argument("--adapter", choices=("memory", "deterministic"),
                   help="the RAM backend the device fabric runs on: seeded "
                        "per run, or the deterministic replay substitutes")
    q.add_argument("--seed", type=int, help="entropy seed for the fabric")
    q.add_argument("--console-in", help="hex bytes to hand the guest console")
    q.add_argument("--devices", action="store_true",
                   help="configure the optional network and wall-clock "
                        "extension devices")
    q.add_argument("--no-check", action="store_true",
                   help="do not compare the result with the application's own "
                        "declared expectations")
    q.add_argument("--skip-gate", action="store_true",
                   help="run even if the PA21 ledger requirements are unmet")
    q.add_argument("--build", action="store_true",
                   help="build first if the source has changed since the last "
                        "build")
    q.add_argument("--trace", nargs="?", type=int, const=256, default=None,
                   metavar="N",
                   help="run one instruction at a time and record where it "
                        "went, up to N steps (default 256)")
    q.add_argument("--unsigned", action="store_true",
                   help="run the raw image instead of the signed one, which "
                        "is the development path the runtime calls "
                        "DEVELOPMENT_RAW")
    q.add_argument("--state", choices=("fresh", "keep"),
                   help="carry the fabric's storage objects and counters over "
                        "from the previous run, or start empty (the default, "
                        "and what the container declares)")
    q.add_argument("--mailbox-in", dest="mailbox_in",
                   help="hex bytes for the host to leave in the mailbox "
                        "before the guest runs, which is the only way "
                        "MAILBOX_GET can return anything")
    q.set_defaults(f=cmd_run)

    q = sub.add_parser("verify", help="verify a built application end to end")
    q.add_argument("app")
    q.set_defaults(f=cmd_verify)

    q = sub.add_parser("list", help="installed containers and applications")
    q.set_defaults(f=cmd_list)

    q = sub.add_parser("describe",
                       help="the language and container contract, for whatever "
                            "is writing the code")
    q.set_defaults(f=cmd_describe)

    q = sub.add_parser("try",
                       help="compile and run a candidate source in one call, "
                            "without leaving a container behind")
    q.add_argument("--from", dest="source", default="-", metavar="FILE",
                   help="source file, or '-' for standard input (the default)")
    q.add_argument("--keep", metavar="NAME",
                   help="promote the candidate into the registry under this "
                        "name instead of discarding it")
    q.add_argument("--requires", nargs="*", default=[],
                   help="PA21 ledger items the candidate declares")
    q.add_argument("--adapter", choices=("memory", "deterministic"),
                   default="deterministic",
                   help="default deterministic, so two candidates are "
                        "comparable")
    q.add_argument("--budget", type=int)
    q.add_argument("--console-in", help="hex bytes for the guest console")
    q.add_argument("--no-run", action="store_true",
                   help="compile only")
    q.add_argument("--fix", action="store_true",
                   help="apply the corrections that have one legal form "
                        "before compiling, and report every edit")
    q.set_defaults(f=cmd_try)

    q = sub.add_parser("trust",
                       help="the signing keys this studio accepts, and adding "
                            "one")
    q.add_argument("add", nargs="?",
                   help="a public key file, or a container that carries one")
    q.set_defaults(f=cmd_trust)

    q = sub.add_parser("fabric",
                       help="the container's state as a live TIFF: read it, "
                            "run it, write it back, in constant flux")
    q.add_argument("action",
                   choices=("init", "tick", "live", "view", "frames"))
    q.add_argument("container")
    q.add_argument("--cols", type=int, default=2,
                   help="shard grid columns (init)")
    q.add_argument("--adapter", choices=("memory", "deterministic"))
    q.add_argument("--mailbox-in", dest="mailbox_in")
    q.add_argument("--no-view", action="store_true",
                   help="do not render a PNG each tick")
    q.add_argument("--ticks", type=int, default=0,
                   help="stop after this many ticks (live); 0 runs until "
                        "interrupted")
    q.add_argument("--interval", type=float, default=0.5,
                   help="seconds between ticks (live)")
    q.add_argument("--until-still", action="store_true",
                   help="stop when the fabric stops changing (live)")
    q.add_argument("--out", help="where to write the PNG (view)")
    q.add_argument("--scale", type=int, default=16,
                   help="pixels per cell in the rendered view")
    q.set_defaults(f=cmd_fabric)

    q = sub.add_parser("doctor",
                       help="what this host can do, what was exercised just "
                            "now, and what is untested here")
    q.set_defaults(f=cmd_doctor)

    q = sub.add_parser("expect",
                       help="record what a container does now as what it is "
                            "expected to do")
    q.add_argument("container")
    q.add_argument("--registers", nargs="*",
                   help="only these registers (default: every one that holds "
                        "something)")
    q.add_argument("--fabric", nargs="*",
                   help="only these fabric keys")
    q.add_argument("--dry-run", action="store_true",
                   help="show what would be recorded without writing it")
    q.add_argument("--state", choices=("fresh", "keep"), default="fresh",
                   help="capture from a fresh fabric (the default, and the "
                        "only reproducible one) or from the carried state")
    q.set_defaults(f=cmd_expect)

    q = sub.add_parser("test",
                       help="run every container against its own declared "
                            "expectations")
    q.add_argument("container", nargs="*", help="only these")
    q.set_defaults(f=cmd_test)

    q = sub.add_parser("abi",
                       help="demonstrate the service ABI the description "
                            "claims, by running a program per claim")
    q.add_argument("--service", help="only this service")
    q.set_defaults(f=cmd_abi)

    q = sub.add_parser("fix",
                       help="apply the corrections a refusal has only one "
                            "form of, and say which were applied")
    q.add_argument("--from", dest="source", default="-", metavar="FILE",
                   help="source file, or '-' for standard input (the "
                        "default); the corrected source goes to stdout and "
                        "the account of what changed to stderr")
    q.add_argument("--write", action="store_true",
                   help="write the corrected source back over the file")
    q.set_defaults(f=cmd_fix)

    q = sub.add_parser("explain",
                       help="what a compiler refusal means, and what to do")
    q.add_argument("message", nargs="+")
    q.set_defaults(f=cmd_explain)

    q = sub.add_parser("watch",
                       help="build and run a container each time you save it")
    q.add_argument("container")
    q.add_argument("--once", action="store_true",
                   help="build and run once, then stop")
    q.add_argument("--rounds", type=int, default=0,
                   help="stop after this many rebuilds")
    q.add_argument("--no-run", action="store_true",
                   help="build only; do not run")
    q.add_argument("--fix", action="store_true",
                   help="apply the corrections that have one legal form to "
                        "the file on save, and report each one")
    q.set_defaults(f=cmd_watch)

    q = sub.add_parser("containers",
                       help="the containers this studio holds, and moving "
                            "them in and out")
    q.add_argument("--state-reset", metavar="NAME", dest="state_reset",
                   help="throw away a container's carried fabric state, so "
                        "its next run starts from an empty fabric")
    q.add_argument("--verify", action="store_true",
                   help="re-derive each container's seal and check its gate")
    q.add_argument("--pack", metavar="NAME",
                   help="zip a container into one .pa21c file")
    q.add_argument("--out", help="where to write the packed archive")
    q.add_argument("--install", metavar="PATH",
                   help="import a .pa21c archive or container directory")
    q.add_argument("--remove", metavar="NAME",
                   help="remove one container from this studio")
    q.add_argument("--force", action="store_true",
                   help="replace a container of the same name on import")
    q.set_defaults(f=cmd_containers)

    q = sub.add_parser("selftest", help="compile and run the canonical "
                                        "applications")
    q.add_argument("--quick", action="store_true")
    q.set_defaults(f=cmd_selftest)

    q = sub.add_parser("ledger", help="read the bound PA21 capability ledger")
    q.add_argument("--pa21", help="delivery root (default: the bound one)")
    q.add_argument("--item", nargs="*", default=[],
                   help="ledger item ids to describe")
    q.set_defaults(f=cmd_ledger)

    q = sub.add_parser("seal", help="re-derive SHA256SUMS for PA21 packages")
    q.add_argument("--pa21", required=True)
    q.add_argument("--limit", type=int, default=0,
                   help="check only the first N listed files per package")
    q.set_defaults(f=cmd_seal)

    q = sub.add_parser("ui", help="open the install/uninstall window")
    q.add_argument("--port", type=int, default=0)
    q.add_argument("--no-browser", action="store_true")
    q.add_argument("--vm", help="pre-fill the VM package path")
    q.add_argument("--pa21", help="pre-fill the PA21 delivery root")
    q.set_defaults(f=cmd_ui)
    return p


def _lift_globals(argv: List[str]) -> Tuple[List[str], bool]:
    """Accept `studio describe --json` as well as `studio --json describe`.

    `--json` is a property of the answer, not of the verb, so argparse wants
    it before the subcommand. Nobody types it there, and this studio's own
    description tells an agent to write `studio describe --json`. Rather than
    make the instruction wrong, the flag is lifted out of wherever it appears.
    """
    lifted = False
    rest: List[str] = []
    for arg in argv:
        if arg == "--json":
            lifted = True
        else:
            rest.append(arg)
    return (["--json"] + rest if lifted else rest), lifted


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = list(sys.argv[1:] if argv is None else argv)
    if "--" not in args:                 # never rewrite past an explicit stop
        args, _ = _lift_globals(args)
    a = p.parse_args(args)
    try:
        return int(a.f(a))
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        return 1
    except StudioError as e:
        payload = {"ok": False, "error": str(e), "detail": e.detail}
        if getattr(a, "json", False):
            print(json.dumps(payload, indent=2, default=str))
        else:
            sys.stderr.write(f"refused: {e}\n")
        return 1


if __name__ == "__main__":                                   # pragma: no cover
    raise SystemExit(main())
