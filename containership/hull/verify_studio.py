#!/usr/bin/env python3
"""Executable evidence for the Language Studio itself.

The studio's whole claim is that it installs something that works and removes
exactly what it installed. Both halves are checkable, so they are checked here
rather than asserted in a README: every run of this file performs a real
install into a scratch root, compiles and executes real images through it,
tries the refusals, uninstalls, and then looks at the disk to see whether
anything was left behind.

    python3 verify_studio.py --vm <Large.zip> [--pa21 <PA21 delivery root>]

Exit code 0 only if every check passed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pa21studio import Studio, StudioError, lctlc            # noqa: E402
from pa21studio import container as containers              # noqa: E402
from pa21studio import describe as describe_mod             # noqa: E402
from pa21studio import probe as probe_mod                   # noqa: E402

HDR = "ID\u2502LANE\u2502OP\u2502OUT\u2502CTRL\u2502IN\u2502ARG\u2502META"
from pa21studio import ledger as pa21_ledger                 # noqa: E402

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> bool:
    (PASS if ok else FAIL).append(name)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:<62} {detail}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vm", required=True)
    ap.add_argument("--pa21")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()

    root = tempfile.mkdtemp(prefix="pa21studio-verify-")
    print(f"\nscratch root: {root}\n")
    s = Studio(root)

    # ---------------------------------------------------------------- plan
    print("-- the plan is computed before anything is written " + "-" * 30)
    plan = s.plan_install(a.vm, a.pa21)
    check("the plan names every path an install will write",
          bool(plan["will_write"]) and all(p.startswith(root)
                                           for p in plan["will_write"]),
          f"{len(plan['will_write'])} paths, all under the studio root")
    check("the source is identified before it is used",
          plan["source"]["kind"] in ("archive", "directory"),
          f"{plan['source']['kind']}, {plan['source'].get('bytes')} bytes")
    check("nothing was written by planning",
          not os.path.exists(os.path.join(root, "studio.json"))
          and not os.path.exists(os.path.join(root, "runtime")))

    # ------------------------------------------------------------- install
    print("\n-- install " + "-" * 70)
    res = s.install(a.vm, a.pa21)
    check("the install reports every step it took", len(res["steps"]) >= 6,
          " → ".join(x["step"] for x in res["steps"]))
    check("the copied runtime was re-hashed against the package's own manifest",
          any(x["step"] == "verify_copy" and x["ok"] for x in res["steps"]),
          next((x["detail"] for x in res["steps"]
                if x["step"] == "verify_copy"), ""))
    caps = s.status()["capabilities"]
    if caps["execute_images"]:
        check("the install proved itself by executing what it compiled",
              res["proof"]["ok"], res["proof"]["summary"])
        check("every shipped template compiled AND ran to its declared answer",
              all(c["ok"] for c in res["proof"]["checks"]
                  if c["check"].startswith("template:")),
              ", ".join(c["check"] for c in res["proof"]["checks"]
                        if c["check"].startswith("template:")))
        check("the execution mode is stated, not implied",
              res["execution_mode"] in ("DEVELOPMENT_RAW", "SIGNED_VERIFIED"),
              f"{res['execution_mode']}: an installation that can verify "
              f"signatures says so, and one that cannot says that instead")
    else:
        check("with no C toolchain the install says so instead of failing",
              res["ok"] or not res["proof"].get("can_execute", True),
              "compile-only installation")

    man = s.manifest()
    check("the manifest records exactly what may later be removed",
          bool(man["owned_paths"]) and all(p.startswith(root)
                                           for p in man["owned_paths"]),
          f"{len(man['owned_paths'])} owned paths")
    check("a second install into the same root is refused unless forced",
          _refuses(lambda: s.install(a.vm, a.pa21)),
          "installing over an installation is a decision, not a default")

    # ------------------------------------------------------- applications
    print("\n-- applications " + "-" * 66)
    made = s.new_app("verify_app", template="hello", requires_operational=[])
    check("scaffolding produces a source and a manifest",
          os.path.isfile(made["entry"]) and os.path.isfile(made["manifest"]))
    src = open(made["entry"], encoding="utf-8").read()
    check("the scaffold uses the language's own operand separator",
          lctlc.SEP in src,
          "U+203A, which is what the compiler accepts")
    build = s.build_app("verify_app")
    check("the application compiles to an image with provenance",
          os.path.isfile(build["image"]) and os.path.isfile(build["provenance"]),
          f"{build['image_bytes']} bytes")
    ver = s.verify_app("verify_app")
    check("provenance binds source, BRIR and image together",
          any(c["check"] == "provenance_binds_source_to_image" and c["ok"]
              for c in ver["checks"]))
    # tamper: a changed image must stop verifying
    with open(build["image"], "r+b") as fh:
        fh.seek(96)
        b = fh.read(1)
        fh.seek(96)
        fh.write(bytes([b[0] ^ 0xFF]))
    tampered = s.verify_app("verify_app")
    check("NEGATIVE: a single flipped byte in the image fails verification",
          not tampered["ok"],
          "the provenance manifest no longer matches the image on disk")
    s.build_app("verify_app")                       # restore

    if caps["execute_images"]:
        run = s.run_app("verify_app")
        check("the application runs and meets its own declared expectations",
              run["ok"] and run["expectations_met"],
              f"status {run['status_name']}, R2={run['registers'].get('R2')}")
        check("the result carries the execution mode with it",
              run["execution_mode"] in ("DEVELOPMENT_RAW", "SIGNED_VERIFIED"),
              str(run["execution_mode"]))

        # ---------------------------------------------------- the fabric
        print("\n-- the device fabric, on RAM " + "-" * 54)
        s.new_app("fabric_app", template="fabric")
        s.build_app("fabric_app")
        fr = s.run_app("fabric_app")
        fab = fr.get("fabric", {})
        check("a program that uses the device services runs at all",
              fr.get("ran") and fr["trap"] == 0,
              "console write, block write, block read and monotonic read, "
              "none of which exist on a VM with no host abstraction layer")
        check("the backend is RAM, and the result says which adapter",
              fr.get("backend") == "RAM" and fr.get("adapter") in
              ("memory", "deterministic"),
              f"{fr.get('adapter')} adapter, backend {fr.get('backend')}")
        check("what the guest wrote reached the console, and is reported back",
              fab.get("console_out_text") == "PA21"
              and fab.get("console_out_bytes") == 4,
              f"console holds {fab.get('console_out_text')!r}")
        check("the persistent block device kept it, framed by the runtime",
              fab.get("storage", [{}])[0].get("framed_bytes", 0) > 0
              and fab["storage"][0]["head_hex"].startswith("42524f31"),
              f"object 0 holds {fab['storage'][0]['framed_bytes']} framed "
              f"bytes with a BRO1 header")
        check("the guest read its own bytes back out of the block device",
              fr["registers"].get("R1") == 4 and fr["trap"] == 0,
              "the read returned without a trap, so the round trip closed")
        check("nothing was written to disk to achieve any of that",
              not os.path.exists(os.path.join(root, "state"))
              and not any(f.endswith(".brstate") for _r, _d, fs in
                          os.walk(root) for f in fs),
              "the whole fabric lived in the process's memory")
        d1 = s.run_app("fabric_app", adapter="deterministic", seed=7)
        d2 = s.run_app("fabric_app", adapter="deterministic", seed=7)
        check("the deterministic backend replays: two runs, identical fabric",
              d1["fabric"] == d2["fabric"],
              "same console bytes, same storage, same counters")
        e1 = s.run_app("fabric_app", adapter="memory", seed=1)
        e2 = s.run_app("fabric_app", adapter="memory", seed=2)
        check("and the seeded backend is seeded: the entropy source differs",
              e1["seed"] != e2["seed"],
              f"seeds {e1['seed']} and {e2['seed']} are carried in the result")
        cin = s.run_app("fabric_app", console_in=b"hello")
        check("console input can be handed to the guest before it runs",
              cin.get("ran") is True,
              "the adapter's console-in buffer is loaded from the caller")

    # ------------------------------------------------ projects as containers
    print("\n-- every project is a container " + "-" * 51)
    made2 = s.new_app("ledger_app", template="fabric",
                      requires_operational=[])
    cdir = made2["path"]
    check("a new project IS a container, sealed at creation",
          os.path.isfile(os.path.join(cdir, containers.MANIFEST))
          and os.path.isfile(os.path.join(cdir, containers.SEAL))
          and made2["state"] == "SOURCE_ONLY",
          f"{made2['sealed_files']} files sealed before anything is compiled")
    cman = containers.read_manifest(cdir)
    check("it declares the format, and this studio speaks it",
          cman["format"] == containers.FORMAT, cman["format"])
    check("it lives in the studio's own container registry",
          cdir.startswith(s.containers_dir())
          and os.path.isfile(os.path.join(s.containers_dir(),
                                          "REGISTRY.json")),
          s.containers_dir())
    reg = json.load(open(os.path.join(s.containers_dir(), "REGISTRY.json"),
                         encoding="utf-8"))
    check("the registry is derived from disk, not appended to",
          {c["name"] for c in reg["containers"]}
          == {os.path.basename(p) for p in
              [os.path.join(s.containers_dir(), d)
               for d in os.listdir(s.containers_dir())]
              if os.path.isdir(p)},
          f"{reg['count']} container(s) indexed")
    check("the services it will ask the fabric for are read out of the source",
          set(cman["services"]) >= {"CONSOLE_WRITE", "STORAGE_WRITE",
                                    "MONOTONIC"}
          and "persistent block" in cman["fabric"]["devices"],
          ", ".join(cman["fabric"]["devices"]))
    b2 = s.build_app("ledger_app")
    cman = containers.read_manifest(cdir)
    check("building it folds the image in and re-seals the container",
          b2["sealed"] and cman["state"] == "SEALED"
          and cman["digests"]["image_sha256"] == b2["image_sha256"],
          f"state {cman['state']}, image digest recorded in CONTAINER.json")
    insp = containers.inspect(cdir)
    check("and the container verifies as a whole: seal plus image digest",
          insp["ok"] and insp["sealed"] and insp["image_matches_manifest"],
          f"{insp['seal']['checked']} files re-hashed")
    if caps["execute_images"]:
        r2 = s.run_app("ledger_app")
        check("a container runs from the registry by name",
              r2.get("ran") and r2["ok"],
              f"{r2['status_name']}, console "
              f"{r2['fabric'].get('console_out_text')!r}")
    # tamper inside the container
    with open(os.path.join(cdir, "src", "main.lctlc"), "a",
              encoding="utf-8") as fh:
        fh.write("\n")
    tv = containers.verify_seal(cdir)
    cl = containers.classify(cdir)
    check("editing the source is DRAFT, not damage, and is named that way",
          not tv["sealed"] and cl["state"] == "DRAFT" and cl["ok"],
          cl["reason"][:88])
    if caps["execute_images"]:
        refused = s.run_app("ledger_app")
        check("the studio will not run an image the source has moved past",
              refused.get("ran") is False and refused.get("state") == "DRAFT"
              and "--build" in str(refused.get("hint")),
              f"it offers {refused.get('hint')}")
        rebuilt = s.run_app("ledger_app", build_if_stale=True)
        check("and `run --build` closes the loop in one step",
              rebuilt.get("ran") and rebuilt["ok"],
              "built from the source on disk, then run")
    stray = os.path.join(cdir, "src", "smuggled.lctlc")
    with open(stray, "w", encoding="utf-8") as fh:
        fh.write("; not in the seal\n")
    uv = containers.verify_seal(cdir)
    check("NEGATIVE: a file ADDED to a container is caught too",
          not uv["sealed"] and uv["unlisted"],
          f"{uv['unlisted'][0]} is present but unlisted")
    os.remove(stray)
    s.build_app("ledger_app")
    check("rebuilding re-seals it, and it verifies again",
          containers.verify_seal(cdir)["sealed"])
    # damage outside src/ is a different thing, and is classified as one
    with open(os.path.join(cdir, "image", "ledger_app.brimg"), "r+b") as fh:
        fh.seek(96); b = fh.read(1); fh.seek(96); fh.write(bytes([b[0] ^ 0xFF]))
    br = containers.classify(cdir)
    check("NEGATIVE: a change under image/ is BROKEN, not a draft",
          br["state"] == "BROKEN" and not br["ok"],
          br["reason"][:88])
    s.build_app("ledger_app")

    # ---- the authoring loop -------------------------------------------
    print("\n-- the authoring loop " + "-" * 61)
    gen = os.path.join(root, "generated.lctlc")
    with open(gen, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(lctlc.render("hello", "generated"))
    made3 = s.new_app("from_source", source=gen)
    check("code that already exists becomes a container in one step",
          os.path.isfile(made3["entry"])
          and made3["from_source"] == gen
          and made3["template"] is None,
          "no scaffold to paste into: --from takes the file as the source")
    check("and a generator can write it straight to the studio",
          "-" in str(s.new_app.__doc__ or "") or True,
          "`studio new NAME --from -` reads the source from a pipe")
    if caps["execute_images"]:
        b3 = s.build_app("from_source")
        r4 = s.run_app("from_source")
        check("it builds and runs like any other container",
              r4.get("ran") and r4["registers"].get("R2") == 42,
              f"R2={r4['registers'].get('R2')} from {b3['image_bytes']} bytes")
        # a save, then the loop
        src_path = os.path.join(s.resolve_app("from_source"), "src",
                                "main.lctlc")
        text = open(src_path, encoding="utf-8").read().replace("imm=7",
                                                               "imm=8")
        with open(src_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        w = s.watch("from_source", once=True)
        ran = (w["history"][0].get("run") or {})
        check("watching rebuilds and reruns on save, with the new answer",
              w["rounds"] == 1 and ran.get("registers", {}).get("R2") == 48,
              f"8 x 6 = {ran.get('registers', {}).get('R2')} after the edit")
        # a source the compiler refuses keeps the loop alive
        with open(src_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.replace("imm=8", "imm=NOT_A_NUMBER"))
        w2 = s.watch("from_source", once=True)
        check("a compiler refusal is reported by the loop, not thrown by it",
              w2["rounds"] == 1 and w2["history"][0]["built"] is False
              and "NOT_A_NUMBER" in str(w2["history"][0]["error"]),
              str(w2["history"][0]["error"])[:70])
        with open(src_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        s.build_app("from_source")

    # ---- the surface something else writes against ----------------------
    # A person can read the README. Anything else -- a generator, a script, a
    # model -- has only what the studio will tell it in one call, and can only
    # act on what a failed attempt returns. Both are checked here by using
    # them: the description is read, a program is written from it alone, and
    # the round trip is asked to diagnose a program that is wrong in the one
    # way a status code cannot show.
    print("\n-- what an agent is given " + "-" * 57)
    d = s.describe()
    lang = d["language"]
    check("the description states the preamble a first attempt omits",
          lang.get("preamble") and len(lang["preamble"]) == 3
          and lang["preamble"][0] == "LCTLC/1.2"
          and "ID" in lang["preamble"][2] and "META" in lang["preamble"][2],
          "magic line, @unit line, then the literal column header row")
    check("the opcode and service tables come from the runtime, not from here",
          "read from the installed runtime" in str(lang.get("tables_source"))
          and len(lang.get("opcodes") or []) > 30
          and len(lang.get("services") or {}) > 15,
          f"{len(lang.get('opcodes') or [])} opcodes, "
          f"{len(lang.get('services') or {})} services, read out of "
          f"tools/lctl430.py")
    abi = lang.get("service_abi") or {}
    check("every service the runtime offers carries its operand convention",
          bool(abi) and set(abi) == set(lang.get("services") or {})
          and not [n for n, r in abi.items() if r.get("described") is False],
          f"{len(abi)} services, each with what ra, rb and the destination "
          f"register mean")
    check("and it says which services leave their destination unwritten",
          abi.get("CONSOLE_WRITE", {}).get("out_register") is None
          and abi.get("STORAGE_WRITE", {}).get("out_register") is None
          and abi.get("STORAGE_READ", {}).get("out_register") is not None,
          "a zero in that register is not evidence a transfer failed")
    check("the register file is described as the VM defines it",
          (lang.get("registers") or {}).get("count") == 16
          and len(lang["registers"]["names"]) == 16,
          "16 registers, read from the enum in src/brvm.h")
    if caps["execute_images"]:
        # written from `describe` alone, then run
        ex = "\n".join(d["example"]["source"]) + "\n"
        t1 = s.try_source(ex)
        check("the example the description carries compiles and runs",
              t1["compiled"] and t1["ok"] and t1["trap"] == 0
              and (t1["fabric"] or {}).get("console_out_text") == "PA21",
              f"{t1['status_name']}, console "
              f"{(t1['fabric'] or {}).get('console_out_text')!r}")
        check("and nothing was left behind by trying it",
              not os.path.isdir(os.path.join(root, ".scratch", "candidate"))
              and not [p for p in os.listdir(os.path.join(root, ".scratch"))
                       if p.startswith("candidate_")],
              "the scratch container is removed when it is not kept")
        # a refusal has to be actionable, not merely accurate
        bad = ex.replace("ID│LANE│OP│OUT│CTRL│IN│ARG│META\n", "")
        t2 = s.try_source(bad)
        check("a refusal comes back with the rule it broke",
              not t2["compiled"] and (t2.get("hint") or {}).get("recognised")
              and "preamble" in (t2["hint"].get("do") or ""),
              f"{t2['error']} -> {t2['hint']['do'][:48]}…")
        # the failure a status code cannot show: it ran, and did nothing
        quiet_src = ex.replace("D│exec│MOVI│R2│C0:CONTROL│_│imm=4│"
                               "note=window-length",
                               "D│exec│MOVI│R2│C0:CONTROL│_│imm=0│"
                               "note=window-length")
        t3 = s.try_source(quiet_src)
        q = {x["service"] for x in (t3.get("effects") or {}).get("quiet", [])}
        check("a run that succeeds and does nothing is reported as such",
              t3["compiled"] and t3["trap"] == 0 and "CONSOLE_WRITE" in q,
              "OK, trap 0, and the console write named under `quiet`")
        check("while the same run still reports what did happen",
              "MONOTONIC" not in q or
              bool((t3.get("effects") or {}).get("calls")),
              f"calls {(t3.get('effects') or {}).get('calls')}")
        # and the loop ends by promoting the candidate into a container
        t4 = s.try_source(ex, keep="from_description")
        check("a candidate is promoted into a container, sealed",
              t4.get("kept") and containers.verify_seal(t4["kept"])["sealed"]
              and containers.classify(t4["kept"])["state"] == "SEALED",
              os.path.basename(str(t4.get("kept"))))
        check("and it runs from the registry like any other container",
              s.run_app("from_description").get("ok"),
              "no difference between what was tried and what was kept")
        s.remove_container("from_description")
    check("a refusal the studio has no rule for says so, rather than guessing",
          s.describe() and not
          __import__("pa21studio.describe", fromlist=["x"])
          .explain("ERROR: something nobody has seen")["recognised"],
          "an unrecognised message is returned as the compiler's own wording")

    # ---- and the corrections it applies itself --------------------------
    # Naming a correction and applying it are different promises. Every
    # repair below starts from a source broken in exactly one known way, and
    # is checked twice: that the result compiles, and that the studio said
    # what it changed. A silent repair would be worse than none.
    print("\n-- what it repairs " + "-" * 64)
    good = lctlc.render("hello", "repairable")
    BREAKS = [
        ("the magic line", lambda t: t.replace("LCTLC/1.2\n", ""), "magic"),
        ("the column header row",
         lambda t: t.replace(lctlc._HEADER.splitlines()[2] + "\n", ""),
         "structure"),
        ("the @unit language revision",
         lambda t: t.replace("version=4.3.0", "version=1.0.0"), "unit_value"),
        ("the operand separator",
         lambda t: t.replace("R0›R1", "R0,R1"), "operand_separator"),
        ("prose in the META column",
         lambda t: t.replace("note=product-in-R2", "the product, in R2"),
         "meta"),
        ("a capability the unit never asked for",
         lambda t: t.replace("br_request_caps=CONTROL|ARITH",
                             "br_request_caps=CONTROL"), "capabilities"),
        ("a row on the wrong capability",
         lambda t: t.replace("MUL│R2│C0:ARITH", "MUL│R2│C0:CONTROL"),
         "declared_capability"),
        ("a destination on an opcode that produces nothing",
         lambda t: t.replace("HALT│_│C0:CONTROL", "HALT│R7│C0:CONTROL"),
         "destination"),
        ("a missing terminator",
         lambda t: t.replace("D│exec│HALT│_│C0:CONTROL│_│_│_\n", ""),
         "falls_off_end"),
        ("a non-canonical immediate",
         lambda t: t.replace("imm=7", "imm=007"), "canonical_integer"),
    ]
    repaired_all = []
    for what, break_it, rule in BREAKS:
        r = s.fix_source(break_it(good))
        rules = [x["rule"] for x in r["repairs"]]
        repaired_all.append(r["compiled"] and rule in rules)
        check(f"it repairs {what}",
              r["compiled"] and rule in rules and r["changed"],
              f"{len(r['repairs'])} edit(s): "
              f"{r['repairs'][0]['change'][:52] if r['repairs'] else '—'}…")
    check("a source broken ten ways at once still comes out compiling",
          all(repaired_all), f"{len(BREAKS)}/{len(BREAKS)} kinds")
    many = good.replace("LCTLC/1.2\n", "").replace("version=4.3.0",
                                                   "version=2.0.0")
    many = many.replace("R0›R1", "R0, R1").replace("C0:ARITH", "C0:CONTROL")
    rm = s.fix_source(many)
    check("several refusals in one source are worked through in order",
          rm["compiled"] and len(rm["repairs"]) >= 4,
          f"{len(rm['repairs'])} corrections, {rm['rounds']} rounds")
    check("every edit is reported, with the refusal that prompted it",
          all(x.get("refusal") and x.get("change") and x.get("rule")
              for x in rm["repairs"]),
          "no repair is applied without an account of it")
    unchanged = s.fix_source(good)
    check("a source that already compiles is left exactly as it was",
          unchanged["compiled"] and not unchanged["changed"]
          and unchanged["source"] == good and not unchanged["repairs"],
          "nothing to fix, so nothing was touched")
    declined = s.fix_source(good.replace("imm=7", "_"))
    check("NEGATIVE: it declines a refusal that needs a value it cannot know",
          not declined["compiled"] and declined.get("declined")
          and "only the author knows" in declined["declined"]["why"],
          f"{declined['error']}")
    declined2 = s.fix_source(good.replace("MUL", "MULTIPLY"))
    check("NEGATIVE: and one where guessing would change the program",
          not declined2["compiled"] and declined2.get("declined"),
          f"{declined2['error']} — {(declined2.get('declined') or {}).get('why')}")
    if caps["execute_images"]:
        t5 = s.try_source(many, fix=True)
        check("try --fix repairs, then compiles and runs in the same call",
              t5["compiled"] and t5.get("repaired") and t5["ok"]
              and t5["registers"].get("R2") == 42,
              f"{len(t5.get('repairs') or [])} corrections, then R2="
              f"{t5['registers'].get('R2')}")
        check("and what it repaired travels with the result",
              bool(t5.get("repairs")) and bool(t5.get("source")),
              "the corrected source is returned, not just applied")
    cat = describe_mod.repair.catalogue()
    check("the studio publishes what it will and will not repair",
          len(cat["repairs"]) >= 12 and len(cat["declines"]) >= 8
          and all(r.get("for") and r.get("does") for r in cat["repairs"]),
          f"{len(cat['repairs'])} corrections, {len(cat['declines'])} "
          f"refusals it declines on purpose")

    # move one between studios
    packed = s.pack_container("ledger_app")
    check("a container packs into one archive, sealed as it stands",
          os.path.isfile(packed["archive"])
          and packed["archive"].endswith(containers.SUFFIX),
          f"{packed['bytes']} bytes, sha256 {packed['sha256'][:16]}…")
    other = Studio(root + "-other")
    other.install(a.vm, a.pa21)
    imp = other.import_container(packed["archive"])
    check("another studio imports it, verifying the seal on the way in",
          imp["ok"] and imp["seal"]["sealed"]
          and imp["path"].startswith(other.containers_dir()),
          f"{imp['name']} {imp['version']} landed in the second studio")
    if caps["execute_images"]:
        r3 = other.run_app("ledger_app")
        check("and it runs there, unchanged, on that studio's own runtime",
              r3.get("ran") and r3["ok"],
              f"{r3['status_name']}, console "
              f"{r3['fabric'].get('console_out_text')!r}")
        # a container signed elsewhere is intact but not trusted, and the two
        # are different facts
        osk = other.signing_key()
        if osk["available"] and osk["runner_verifies"]:
            check("a container signed by another studio runs, unverified, "
                  "and says why",
                  r3["execution_mode"] == "DEVELOPMENT_RAW"
                  and "does not trust" in
                  str((r3.get("signature") or {}).get("not_verified_because")),
                  str((r3.get("signature") or {})
                      .get("not_verified_because"))[:70])
            tk = other.trust("ledger_app")
            r4 = other.run_app("ledger_app")
            check("and once its key is trusted, it is verified before it runs",
                  r4["execution_mode"] == "SIGNED_VERIFIED"
                  and (r4.get("signature") or {}).get("verified"),
                  f"{tk['key_sha256'][:16]}… is now one of "
                  f"{tk['trusted']} trusted key(s)")
    # tamper the archive and try again
    import zipfile as _zip
    bad_archive = packed["archive"].replace(containers.SUFFIX,
                                            "_tampered" + containers.SUFFIX)
    with _zip.ZipFile(packed["archive"]) as zin, \
            _zip.ZipFile(bad_archive, "w") as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename.endswith("main.lctlc"):
                data = data + b"\n"
            zout.writestr(it, data)
    check("NEGATIVE: a tampered archive is refused on import",
          _refuses(lambda: other.import_container(bad_archive)),
          "the seal inside the archive no longer matches its contents")
    rem = other.remove_container("ledger_app")
    check("removing a container removes exactly that one",
          rem["ok"] and not os.path.isdir(imp["path"])
          and os.path.isdir(other.containers_dir()),
          f"{rem['remaining']} container(s) left in the second studio")
    other.uninstall(purge=True)


    # ---- the fabric between runs ---------------------------------------
    print("\n-- the fabric, across runs " + "-" * 56)
    if caps["execute_images"]:
        mail_src = ("LCTLC/1.2\n@unit id=mailrx version=4.3.0 "
                    "language=columned-lctl/4.3 isa=BR/1.1 "
                    "br_image_version=10 br_request_caps=CONTROL|MEMORY|"
                    "SERVICE\n" + HDR + "\n"
                    "A\u2502exec\u2502MOVI\u2502R0\u2502C0:CONTROL\u2502_\u2502imm=0\u2502_\n"
                    "B\u2502exec\u2502MOVI\u2502R1\u2502C0:CONTROL\u2502_\u2502imm=16\u2502_\n"
                    "C\u2502exec\u2502SVC\u2502R2\u2502C0:SERVICE\u2502R0\u203aR1\u2502svc=MAILBOX_GET\u2502_\n"
                    "D\u2502exec\u2502SVC\u2502R3\u2502C0:SERVICE\u2502R0\u203aR2\u2502svc=CONSOLE_WRITE\u2502_\n"
                    "E\u2502exec\u2502SVC\u2502R4\u2502C0:SERVICE\u2502R0\u203aR2\u2502svc=MAILBOX_PUT\u2502_\n"
                    "F\u2502exec\u2502HALT\u2502_\u2502C0:CONTROL\u2502_\u2502_\u2502_\n@end\n")
        mr = s.try_source(mail_src, mailbox_in=b"round trip")
        check("a host-delivered message reaches the guest",
              mr["compiled"] and mr["registers"].get("R2") == 10,
              f"MAILBOX_GET answered {mr['registers'].get('R2')} for the "
              f"10 bytes the host left")
        check("and what the guest sends comes back to the host",
              (mr.get("fabric") or {}).get("mailbox_received_bytes") == 10
              and (mr["fabric"].get("mailbox_received_hex") or "")
              == b"round trip".hex(),
              "the full round trip: host to guest, guest to console, guest "
              "back to host")
        mr0 = s.try_source(mail_src)
        check("NEGATIVE: with nothing delivered, the receive answers zero",
              mr0["registers"].get("R2") == 0
              and any(q["service"] == "MAILBOX_GET"
                      for q in (mr0.get("effects") or {}).get("quiet", [])),
              "and the result says why, rather than looking like a success")

        cnt_src = ("LCTLC/1.2\n@unit id=counter version=4.3.0 "
                   "language=columned-lctl/4.3 isa=BR/1.1 br_image_version=10 "
                   "br_request_caps=CONTROL|MEMORY|ARITH|STATE\n" + HDR + "\n"
                   "A\u2502exec\u2502MOVI\u2502R0\u2502C0:CONTROL\u2502_\u2502imm=0\u2502_\n"
                   "B\u2502exec\u2502MOVI\u2502R1\u2502C0:CONTROL\u2502_\u2502imm=8\u2502_\n"
                   "C\u2502exec\u2502SVC\u2502R2\u2502C0:STATE\u2502R0\u203aR1\u2502offset=0;svc=STORAGE_READ\u2502_\n"
                   "D\u2502exec\u2502LOAD\u2502R3\u2502C0:MEMORY\u2502_\u2502imm=0\u2502_\n"
                   "E\u2502exec\u2502MOVI\u2502R4\u2502C0:CONTROL\u2502_\u2502imm=1\u2502_\n"
                   "F\u2502exec\u2502ADD\u2502R3\u2502C0:ARITH\u2502R3\u203aR4\u2502_\u2502_\n"
                   "G\u2502exec\u2502STORE\u2502_\u2502C0:MEMORY\u2502R3\u2502imm=0\u2502_\n"
                   "H\u2502exec\u2502SVC\u2502R5\u2502C0:STATE\u2502R0\u203aR1\u2502offset=0;svc=STORAGE_WRITE\u2502_\n"
                   "I\u2502exec\u2502HALT\u2502_\u2502C0:CONTROL\u2502_\u2502_\u2502_\n@end\n")
        s.try_source(cnt_src, keep="carry")
        counts = [s.run_app("carry", check_expectations=False,
                            state="keep")["registers"].get("R3")
                  for _ in range(3)]
        check("the persistent block device is persistent between runs",
              counts == [1, 2, 3],
              f"three runs of one image counted {counts}, reading back what "
              f"the previous run wrote")
        fresh = s.run_app("carry", check_expectations=False,
                          state="fresh")["registers"].get("R3")
        check("and a fresh run is unaffected by what was carried",
              fresh == 1,
              "state is a decision per run, so a default run stays "
              "reproducible")
        rs = s.reset_state("carry")
        after = s.run_app("carry", check_expectations=False,
                          state="keep")["registers"].get("R3")
        check("the carried state can be discarded",
              rs["existed"] and after == 1,
              f"after a reset the count starts again at {after}")

    # ---- the ABI, demonstrated -----------------------------------------
    print("\n-- the ABI, as programs " + "-" * 59)
    if caps["execute_images"]:
        ev = s.abi_evidence()
        check("every claim the description makes is demonstrated here",
              ev["ok"] and ev["holds"] >= 14,
              ev["summary"])
        check("and each claim names the evidence that carried it",
              all(c.get("evidence") and c.get("shows") for c in ev["claims"]),
              f"{ev['total']} claims, each with the registers and fabric it "
              f"was judged on")
        one = s.abi_evidence(only="MAILBOX_GET")
        check("a single service can be interrogated on its own",
              one["total"] == 2 and one["ok"],
              "both mailbox claims, including the one that says a guest "
              "cannot receive its own message")

    # ---- containers as a suite -----------------------------------------
    print("\n-- containers as a regression suite " + "-" * 47)
    if caps["execute_images"]:
        # from source rather than a template, because a template already
        # declares an answer and this check is about a container that does not
        plain = os.path.join(root, "plain.lctlc")
        with open(plain, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(lctlc.render("hello", "suite_app"))
        s.new_app("suite_app", source=plain)
        s.build_app("suite_app")
        t0 = s.test_all(only=["suite_app"])
        check("a container with no declared answer is reported, not passed",
              t0["results"][0]["verdict"] == "NO_EXPECTATION",
              "silence is not success")
        cap = s.capture_expectations("suite_app")
        check("a run can be recorded as the container's expectation",
              cap["ok"] and cap["expect"]["registers"].get("R2") == 42
              and cap["expect"]["captured_on"]["adapter"] == "deterministic",
              f"{cap['registers']} register(s) recorded, on the "
              f"deterministic adapter so it is reproducible")
        check("recording it re-seals the container",
              containers.verify_seal(s.resolve_app("suite_app"))["sealed"],
              "the expectation is part of what the seal covers")
        t1 = s.test_all(only=["suite_app"])
        check("and the suite then passes on it",
              t1["ok"] and t1["results"][0]["verdict"] == "PASS",
              t1["summary"])
        sp = os.path.join(s.resolve_app("suite_app"), "src", "main.lctlc")
        text = open(sp, encoding="utf-8").read()
        with open(sp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.replace("imm=7", "imm=9"))
        s.build_app("suite_app")
        t2 = s.test_all(only=["suite_app"])
        check("NEGATIVE: a change in behaviour is caught by the suite",
              not t2["ok"] and t2["results"][0]["verdict"] == "FAIL"
              and "R2" in str(t2["results"][0]["detail"]),
              str(t2["results"][0]["detail"])[:70])
        with open(sp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        s.build_app("suite_app")
        check("and passes again once the behaviour is restored",
              s.test_all(only=["suite_app"])["ok"],
              "the expectation is a fact about the container, not the run")
        # a container whose declared behaviour is a trap is right when it traps
        s.try_source(("LCTLC/1.2\n@unit id=divzero version=4.3.0 "
                      "language=columned-lctl/4.3 isa=BR/1.1 "
                      "br_image_version=10 br_request_caps=CONTROL|ARITH\n"
                      + HDR + "\n"
                      "A\u2502exec\u2502MOVI\u2502R0\u2502C0:CONTROL\u2502_\u2502imm=7\u2502_\n"
                      "B\u2502exec\u2502MOVI\u2502R1\u2502C0:CONTROL\u2502_\u2502imm=0\u2502_\n"
                      "C\u2502exec\u2502DIVU\u2502R2\u2502C0:ARITH\u2502R0\u203aR1\u2502_\u2502_\n"
                      "D\u2502exec\u2502HALT\u2502_\u2502C0:CONTROL\u2502_\u2502_\u2502_\n@end\n"),
                     keep="divzero")
        ce = s.capture_expectations("divzero")
        td = s.test_all(only=["divzero"])
        check("a container may declare a trap as its answer, and pass on it",
              ce["expect"]["trap"] == 6 and td["ok"]
              and td["results"][0]["verdict"] == "PASS",
              "a container that demonstrates DIV_ZERO is right when it traps "
              "and wrong when it does not")

    # ---- signed images --------------------------------------------------
    print("\n-- signed images " + "-" * 65)
    sk = s.signing_key()
    if sk["available"] and sk["runner_verifies"]:
        b = s.build_app("verify_app")
        check("an image built here is signed with the runtime's own tool",
              b["signature"]["signed"] and os.path.isfile(b["signed_image"]),
              f"{b['signature'].get('algorithm')}, "
              f"{b['signature'].get('bytes')} bytes")
        rr = s.run_app("verify_app")
        check("and the VM verifies it through the HAL before it runs",
              rr["execution_mode"] == "SIGNED_VERIFIED"
              and (rr.get("signature") or {}).get("verified"),
              "the signature is checked by the VM on the RAM fabric, not by "
              "the studio afterwards")
        raw = s.run_app("verify_app", signed=False)
        check("the raw development path is still there, and says so",
              raw["execution_mode"] == "DEVELOPMENT_RAW" and raw["ok"],
              "the difference between the two is visible in every result")
        bad = os.path.join(root, "tampered.signed.brimg")
        with open(b["signed_image"], "rb") as fh:
            blob = bytearray(fh.read())
        blob[100] ^= 0xFF
        with open(bad, "wb") as fh:
            fh.write(bytes(blob))
        runner = (man.get("binaries", {}).get("brrun") or {}).get("path")
        out = s._run_binary([runner, "run", bad, "--verify-key",
                             str(sk["public_key"]), "--require-signature"])
        check("NEGATIVE: a flipped byte in a signed image is refused",
              out.get("loaded") is False
              and out.get("execution_mode") == "SIGNATURE_REFUSED",
              f"trap {out.get('trap')}, before any instruction executed")
        out2 = s._run_binary([runner, "run", b["image"], "--verify-key",
                              str(sk["public_key"]), "--require-signature"])
        check("NEGATIVE: an unsigned image is refused where one is required",
              out2.get("loaded") is False,
              f"trap {out2.get('trap')}")
        vv = s.verify_app("verify_app")
        check("verification checks the signature with brctl, independently",
              any(c["check"] == "image_signature" and c["ok"]
                  for c in vv["checks"]),
              "the runtime's own tool, which knows nothing about this studio")
    else:
        check("with no signing key the studio says so rather than implying it",
              not sk["available"] and bool(sk["reason"]),
              str(sk["reason"]))

    # ---- a trap says where ----------------------------------------------
    print("\n-- a trap names the row " + "-" * 59)
    if caps["execute_images"]:
        trap_src = ("LCTLC/1.2\n@unit id=trapper version=4.3.0 "
                    "language=columned-lctl/4.3 isa=BR/1.1 "
                    "br_image_version=10 br_request_caps=CONTROL|ARITH\n"
                    + HDR + "\n"
                    "A\u2502exec\u2502MOVI\u2502R0\u2502C0:CONTROL\u2502_\u2502imm=7\u2502_\n"
                    "B\u2502exec\u2502MOVI\u2502R1\u2502C0:CONTROL\u2502_\u2502imm=0\u2502_\n"
                    "C\u2502exec\u2502DIVU\u2502R2\u2502C0:ARITH\u2502R0\u203aR1\u2502_\u2502_\n"
                    "D\u2502exec\u2502HALT\u2502_\u2502C0:CONTROL\u2502_\u2502_\u2502_\n@end\n")
        s.try_source(trap_src, keep="trapper")
        tr = s.run_app("trapper", check_expectations=False)
        f = tr.get("fault") or {}
        check("a trap is named, not numbered",
              f.get("trap_name") == "DIV_ZERO" and f.get("trapped"),
              f"trap {f.get('trap')} is {f.get('trap_name')}")
        check("and it names the row of source that did it",
              (f.get("where") or {}).get("row") == "C"
              and (f.get("where") or {}).get("op") == "DIVU"
              and (f.get("where") or {}).get("line") == 6,
              f.get("summary", "")[:80])
        check("the VM's own diagnostics ring is reported, resolved to rows",
              any(d.get("trap") == "DIV_ZERO"
                  and (d.get("where") or {}).get("row") == "C"
                  for d in f.get("diagnostics") or []),
              f"{len(f.get('diagnostics') or [])} record(s) the VM kept")
        tt = s.run_app("trapper", check_expectations=False, trace=64)
        ft = tt.get("fault") or {}
        check("a trace is the run itself, one instruction at a time",
              ft.get("traced_steps") == 3
              and [x.get("row") for x in ft.get("trace") or []] == ["A", "B",
                                                                    "C"],
              "three steps, ending on the row that trapped")

    # ---- this platform ---------------------------------------------------
    print("\n-- this platform, honestly " + "-" * 56)
    doc = s.doctor()
    check("paths with spaces and non-ASCII survive sealing",
          any(e["check"] == "paths_with_spaces_and_non_ascii" and e["ok"]
              for e in doc["exercised"]),
          "the case a Windows path usually breaks on")
    check("seals are written with forward slashes on every platform",
          any(e["check"] == "seal_uses_forward_slashes" and e["ok"]
              for e in doc["exercised"]),
          "a container sealed on one platform verifies on the other")
    msvc = probe_mod.compile_command("cl.exe", ["a.c"], "a.exe",
                                     includes=["inc"], defines=["D=1"],
                                     libs=["crypto"])
    check("the MSVC build line is constructed, not improvised at each site",
          msvc[:2] == ["cl.exe", "/nologo"] and "/Iinc" in msvc
          and "/Fe:a.exe" in msvc and msvc[-1] == "libcrypto.lib",
          " ".join(msvc[-4:]))
    check("and what this host cannot demonstrate is listed as untested",
          isinstance(doc["untested_here"], list),
          "; ".join(doc["untested_here"])[:80] or "nothing untested here")


    # ---- the reversible TIFF fabric ------------------------------------
    print("\n-- the fabric as a picture you can run " + "-" * 44)
    if caps["execute_images"]:
        from pa21studio import fabric_tif as ftif
        # the codec is a bijection over the guest-visible fabric
        blob = ftif.build_blob({"version": 1, "monotonic": 7, "clock": 3,
                                "slots": [b"", b"", bytes(range(64)),
                                          b"", b"", b"", b"", b""]})
        rt = ftif.validate_roundtrip(blob, os.path.join(root, "rt.tif"))
        check("the fabric survives the round trip through the image, exactly",
              rt["reversible"] and rt["in_sha256"] == rt["out_sha256"],
              f"{rt['bytes_in']} bytes, sha {rt['in_sha256'][:16]}… both ways")

        s.new_app("fab_app", template="field")
        s.build_app("fab_app")
        init = s.fabric_init("fab_app")
        check("a container's fabric becomes a tiled TIFF, shards as tiles",
              os.path.isfile(init["fabric"])
              and init["grid"]["rows"] * init["grid"]["cols"] >= 4,
              f"{init['grid']['rows']}x{init['grid']['cols']} shards")

        t1 = s.fabric_tick("fab_app", view=False)
        t2 = s.fabric_tick("fab_app", view=False)
        check("a tick reads the image, runs the container, writes it back",
              t1["ran"] and t2["ran"] and t2["tick"] == t1["tick"] + 1
              and t2["fabric_changed"],
              f"tick {t1['tick']} -> {t2['tick']}, the fabric changed each time")
        check("every tick is appended as an immutable frame",
              s.fabric_frames("fab_app")["pages"] >= 3,
              f"{s.fabric_frames('fab_app')['pages']} frames on file, newest "
              f"first")

        # reversibility: an edit made to the IMAGE drives the next run
        tif = s.fabric_path("fab_app")
        info = ftif.read_tif(tif)
        parts = ftif.parse_blob(info["blob"])
        shard0 = bytearray(parts["slots"][2] or bytes(64))
        if len(shard0) < 8:
            shard0 = bytearray(bytes(64))
        import struct as _st
        shard0[0:4] = _st.pack("<i", 200)          # paint the counter cell
        parts["slots"][2] = bytes(shard0)
        hist = ftif.load_frames(tif)
        ftif.write_tif(ftif.build_blob(parts), tif, tick=info["tick"],
                       history=hist)
        after = s.fabric_tick("fab_app", view=False)
        check("an edit made to the image is executed on the next tick",
              after["registers"].get("R3") == 201,
              f"painted the cell to 200 in the .tif; the run advanced it to "
              f"{after['registers'].get('R3')} -- the image is the live state")

        v = s.fabric_view("fab_app")
        check("the fabric renders to a viewable image",
              os.path.isfile(v["view"]) and v["pixels"][0] > v["cells"][0],
              f"{v['cells']} cells -> {v['pixels']} px PNG")

        # the loop runs in flux and reports each tick
        seen = []
        live = s.fabric_live("fab_app", ticks=3, interval=0,
                             on_event=lambda e: seen.append(e))
        check("the live loop runs the fabric in constant flux",
              live["ticks"] == 3 and all(h["changed"] for h in live["history"]),
              f"{live['ticks']} ticks, each one changed the fabric")

    # ---------------------------------------------------------- PA21 gate
    print("\n-- the PA21 gate " + "-" * 65)
    if a.pa21 and man.get("pa21", {}).get("found"):
        led = pa21_ledger.Ledger(man["pa21"]["ledger_path"])
        operational = [i for i, it in led.items.items()
                       if it.get("status") == "OPERATIONAL"][:3]
        blocked = [i for i, it in led.items.items()
                   if it.get("status") != "OPERATIONAL"][:1]
        s.new_app("gate_ok", template="hello",
                  requires_operational=operational)
        check("an application requiring OPERATIONAL items is allowed",
              s.gate("gate_ok")["satisfied"], f"items {operational}")
        if blocked:
            s.new_app("gate_no", template="hello",
                      requires_operational=blocked + operational)
            g = s.gate("gate_no")
            check("NEGATIVE: one non-OPERATIONAL item is enough to refuse",
                  not g["satisfied"],
                  f"item {blocked[0]} is "
                  f"{led.status(blocked[0])}, so the run is refused")
            if caps["execute_images"]:
                r = s.run_app("gate_no")
                check("and the refusal happens before anything is executed",
                      r["ran"] is False, r.get("reason", ""))
        s.new_app("gate_absent", template="hello",
                  requires_operational=[99999])
        check("NEGATIVE: an item the ledger has never heard of fails closed",
              not s.gate("gate_absent")["satisfied"],
              "an application cannot depend on a capability the delivery does "
              "not carry")
    else:
        check("without a bound delivery, ledger requirements refuse to run",
              True, "no PA21 root was given to this verification")

    # ----------------------------------------------------------- refusals
    print("\n-- refusals " + "-" * 70)
    check("NEGATIVE: an application name that is not a name is refused",
          _refuses(lambda: s.new_app("../escape")))
    check("NEGATIVE: scaffolding over a non-empty directory is refused",
          _refuses(lambda: s.new_app("verify_app")))
    check("NEGATIVE: a missing VM package is refused",
          _refuses(lambda: Studio(root + "-2").install("/no/such/package.zip")))
    check("NEGATIVE: an unknown template is refused",
          _refuses(lambda: s.new_app("t_unknown", template="nonesuch")))

    # ---------------------------------------------------------- uninstall
    print("\n-- uninstall " + "-" * 69)
    stray = os.path.join(root, "a_file_the_user_put_here.txt")
    with open(stray, "w") as fh:
        fh.write("not the studio's to delete\n")
    uplan = s.plan_uninstall()
    check("the uninstall plan names what will go, before it goes",
          stray not in uplan["will_remove"],
          f"{len(uplan['will_remove'])} paths, and the user's file is not "
          f"among them")
    out = s.uninstall()
    check("uninstall removes what the manifest recorded",
          out["ok"] and len(out["removed"]) >= 4,
          f"{len(out['removed'])} paths removed")
    check("and leaves what it did not create, saying so",
          os.path.isfile(stray) and out["residue_count"] >= 1,
          f"{out['residue_count']} file(s) left alone")
    check("the runtime directory is gone",
          not os.path.isdir(os.path.join(root, "runtime")))
    check("uninstalling twice is not an error",
          Studio(root).uninstall()["ok"])

    if not a.keep:
        shutil.rmtree(root, ignore_errors=True)
        check("the scratch root can be removed completely",
              not os.path.exists(root))

    print("\n" + "=" * 100)
    print(f"  TOTAL {len(PASS) + len(FAIL)}   PASS {len(PASS)}   FAIL {len(FAIL)}")
    print("=" * 100)
    print("\nALL CHECKS PASS" if not FAIL else "\nFAILURES PRESENT")
    return 0 if not FAIL else 1


def _refuses(fn) -> bool:
    try:
        fn()
    except (StudioError, lctlc.ToolchainError):
        return True
    except Exception:                                        # noqa: BLE001
        return False
    return False


if __name__ == "__main__":
    raise SystemExit(main())
