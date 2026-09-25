"""Deterministic generation of the committed reference matrix and proof records (MC-12, MC-13, MC-31).

``python -m inv22_alternative_wasi_branch.reference --check`` fails if the
committed ``data/matrix.json`` differs from what the sources + reviewed
overrides produce, so hand edits cannot drift into a release.
"""
from __future__ import annotations

import json
import pathlib
import sys

from . import canonical, matrix

PKG = pathlib.Path(__file__).resolve().parent
LEGACY_ALIASES = {"clocks": "wasi:clocks", "random": "wasi:random", "filesystem": "wasi:filesystem/types",
                  "sockets": "wasi:sockets", "threads": "wasi:threads"}


def _baseline_ids() -> tuple[dict, dict]:
    man = json.loads((PKG / "baselines/manifest.json").read_text(encoding="utf-8"))
    return ({"id": "UNPINNED:standards", "digest": canonical.digest(man["standards"])},
            {"id": "UNPINNED:fork", "digest": canonical.digest(man["fork"])})


def reviewed_overrides() -> dict:
    return json.loads((PKG / "data/overrides.json").read_text(encoding="utf-8"))["overrides"]


def build_reference() -> dict:
    src, dst = _baseline_ids()
    entries = []
    for iface, ov in sorted(reviewed_overrides().items()):
        e = {"interface": iface, "classification": ov["classification"], "rationale": ov["rationale"],
             "source_version": ov["source_version"], "target_version": ov["target_version"]}
        if ov["classification"] == "shimmable":
            e["shim_id"], e["proof_ref"] = ov["shim_id"], ov["proof_ref"]
        entries.append(e)
    return matrix.build(entries, revision=1, source_baseline=src, target_baseline=dst,
                        generated_at="2026-09-23T00:00:00Z", producer="inv22.reference/4.3.0")


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    doc = build_reference()
    out = PKG / "data/matrix.json"
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if "--check" in argv:
        same = out.exists() and json.loads(out.read_text(encoding="utf-8")) == doc
        print("reference matrix: " + ("in sync" if same else "DRIFT - regenerate"))
        return 0 if same else 1
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({matrix.parse(doc).digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
