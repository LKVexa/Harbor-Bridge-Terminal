#!/usr/bin/env python3
"""Scripting the studio from an application.

This is the shape a host application takes when it wants to run COLUMNED LCTL
work on a PA21.31 delivery: install once if needed, declare which ledger items
the work depends on, and let the studio refuse when the delivery does not carry
them. Nothing here parses console output -- every call returns a dict.

    python3 examples/embed_studio.py --vm <Large.zip> --pa21 <PA21.2 root>
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pa21studio import Studio, StudioError                    # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vm", required=True, help="the container VM package")
    ap.add_argument("--pa21", help="the PA21 delivery root")
    ap.add_argument("--root", help="studio root (a scratch one is fine)")
    ap.add_argument("--keep", action="store_true",
                    help="leave the installation in place at the end")
    a = ap.parse_args()

    studio = Studio(a.root)

    # 1. Install only if this root does not already carry one. `status` is
    #    cheap and answers without side effects.
    st = studio.status()
    if not st["installed"]:
        print(f"installing into {studio.root}")
        res = studio.install(vm_source=a.vm, pa21_root=a.pa21,
                             on_event=lambda e: print(f"   {e.get('phase')}: "
                                                      f"{e.get('message','')}"))
        if not res["ok"]:
            print("install did not prove itself:",
                  json.dumps(res["proof"], indent=2)[:800])
            return 1
    else:
        print(f"already installed at {studio.root}")

    # 2. Can this machine execute images at all? The answer is a fact about
    #    the machine, not about the studio, and it is worth branching on
    #    rather than discovering through a failure.
    caps = studio.status()["capabilities"]
    print("capabilities:", json.dumps(caps))

    # 3. Declare the work. The ledger items are the application's contract
    #    with the delivery: it will not run against one that does not carry
    #    them as OPERATIONAL.
    name = "example_pricing"
    if not any(x["name"] == name for x in studio.list_apps()["apps"]):
        made = studio.new_app(name, template="loop",
                              requires_operational=[181, 209, 262])
        print("scaffolded", made["path"])

    build = studio.build_app(name)
    print(f"built {build['name']}: {build['image_bytes']} bytes, "
          f"sha256 {build['image_sha256'][:16]}…")

    verify = studio.verify_app(name)
    print("verified:", verify["ok"])
    for c in verify["checks"]:
        print(f"   {'ok ' if c['ok'] else 'NOT'} {c['check']}")

    if not caps["execute_images"]:
        print("this machine cannot execute images; stopping at a verified "
              "image, which is the honest stopping point")
        return 0

    run = studio.run_app(name)
    if not run.get("ran"):
        print("refused:", run.get("reason"))
        return 1
    print(f"ran: {run['status_name']} trap={run['trap']} "
          f"R2={run['registers'].get('R2')} in {run['seconds']}s")
    print("expectations met:", run.get("expectations_met"))

    if not a.keep:
        out = studio.uninstall(purge=True)
        print(f"uninstalled: {len(out['removed'])} path(s) removed, "
              f"{out['residue_count']} left alone")
    return 0 if run.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
