"""MC-001 / MC-019 -- WIT surface extraction, lock, diff gate, capability map.

A deliberately small parser for the subset of WIT used by INV-13 (packages,
interfaces, resources, funcs, worlds with import/export).  It is sufficient to
compute the *declared surface* (world -> imported interfaces -> functions) and
fail CI on any unapproved change.  It is not a general WIT implementation;
binding generation for guest languages is an external toolchain step
(wit-bindgen) recorded as an open item.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

WIT_DIR = Path(__file__).resolve().parents[1] / "wit"
INTERFACE_CAPABILITY = {
    "filesystem": ["filesystem"], "clocks": ["wall-clock", "monotonic-clock"], "random": ["random"],
    "stdio": ["stdio"], "environment": ["environment"], "sockets": ["sockets"],
    "http-outgoing": ["http-outgoing"], "types": [],
}

_PKG = re.compile(r"^\s*package\s+([a-z0-9-]+):([a-z0-9-]+)@(\d+\.\d+\.\d+)\s*;", re.M)
_BLOCK = re.compile(r"^(interface|world)\s+([a-z0-9-]+)\s*\{", re.M)
_FUNC = re.compile(r"^\s*([a-z0-9-]+)\s*:\s*func\((.*?)\)\s*(->\s*(.*?))?;", re.M)
_IMPORT = re.compile(r"^\s*(import|export)\s+([a-z0-9-]+)\s*;", re.M)


def _strip(src: str) -> str:
    return "\n".join(line.split("//")[0] for line in src.splitlines())


def _blocks(src: str):
    for m in _BLOCK.finditer(src):
        depth, i = 1, m.end()
        while depth and i < len(src):
            depth += {"{": 1, "}": -1}.get(src[i], 0)
            i += 1
        if depth:
            raise ValueError(f"unbalanced braces in {m.group(2)}")
        yield m.group(1), m.group(2), src[m.end():i - 1]


def parse(src: str) -> dict[str, Any]:
    clean = _strip(src)
    pk = _PKG.search(clean)
    if not pk:
        raise ValueError("WIT package declaration with exact semver is required")
    out: dict[str, Any] = {"package": f"{pk.group(1)}:{pk.group(2)}", "version": pk.group(3),
                           "interfaces": {}, "worlds": {}}
    for kind, name, body in _blocks(clean):
        if kind == "interface":
            funcs = {f.group(1): f"func({' '.join(f.group(2).split())}){' -> ' + f.group(4).strip() if f.group(4) else ''}"
                     for f in _FUNC.finditer(body)}
            out["interfaces"][name] = dict(sorted(funcs.items()))
        else:
            items = [(k, n) for k, n in _IMPORT.findall(body)]
            for k, n in items:
                if n not in out["interfaces"]:
                    raise ValueError(f"world {name} {k}s undeclared interface {n}")
            out["worlds"][name] = {"imports": sorted(n for k, n in items if k == "import"),
                                   "exports": sorted(n for k, n in items if k == "export")}
    for iface in out["interfaces"]:
        if iface not in INTERFACE_CAPABILITY:
            raise ValueError(f"interface {iface} has no capability mapping")
    return out


def surface(wit_dir: Path = WIT_DIR) -> dict[str, Any]:
    files = sorted(wit_dir.glob("*.wit"))
    if len(files) != 1:
        raise ValueError("exactly one WIT package file expected")
    src = files[0].read_text(encoding="utf-8")
    parsed = parse(src)
    worlds = {}
    for w, spec in parsed["worlds"].items():
        caps = sorted({c for i in spec["imports"] for c in INTERFACE_CAPABILITY[i]})
        funcs = sorted(f"{i}.{fn}" for i in spec["imports"] for fn in parsed["interfaces"][i])
        worlds[w] = {"imports": spec["imports"], "exports": spec["exports"], "capabilities": caps,
                     "functions": funcs}
    return {"package": parsed["package"], "version": parsed["version"],
            "sha256": hashlib.sha256(src.encode()).hexdigest(), "interfaces": parsed["interfaces"],
            "worlds": worlds}


def diff(approved: dict[str, Any], current: dict[str, Any]) -> list[str]:
    problems = []
    for w, spec in current["worlds"].items():
        a = approved["worlds"].get(w)
        if a is None:
            problems.append(f"new world {w} not approved")
            continue
        for key in ("imports", "exports", "capabilities", "functions"):
            added = sorted(set(spec[key]) - set(a[key]))
            if added:
                problems.append(f"world {w} adds {key}: {added}")
    for i, fns in current["interfaces"].items():
        old = approved["interfaces"].get(i, {})
        for fn, sig in old.items():
            if fn not in fns:
                problems.append(f"breaking: {i}.{fn} removed")
            elif fns[fn] != sig:
                problems.append(f"breaking: {i}.{fn} signature changed")
    return problems


def world_capabilities(world: str) -> frozenset[str]:
    return frozenset(surface()["worlds"][world]["capabilities"])


if __name__ == "__main__":  # pragma: no cover
    import sys
    root = Path(__file__).resolve().parents[1]
    cur = surface()
    if sys.argv[1:] == ["lock"]:
        (root / "WIT.lock").write_text(json.dumps({"package": cur["package"], "version": cur["version"],
                                                   "sha256": cur["sha256"]}, indent=2) + "\n")
        (root / "APPROVED_SURFACE.json").write_text(json.dumps(cur, indent=2, sort_keys=True) + "\n")
        print("locked", cur["sha256"])
    else:
        approved = json.loads((root / "APPROVED_SURFACE.json").read_text())
        lock = json.loads((root / "WIT.lock").read_text())
        probs = diff(approved, cur) + ([] if lock["sha256"] == cur["sha256"] else ["WIT.lock digest mismatch"])
        print(json.dumps({"ok": not probs, "problems": probs}))
        sys.exit(1 if probs else 0)
