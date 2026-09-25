"""Official-tool differential testing (INV11-MC-11).

Compares this front end against the pinned authoritative toolchain
(`wasm-tools component wit --json`, version in ops.MATRIX).  Both sides are
projected into one neutral view (aliases dereferenced, named types nominal,
resource members in `[method]R.m` form with explicit `self`).  If the tool is
absent the result is BLOCKED — never a pass.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any

from .ops import MATRIX
from .resolve import Resolved

ENV = "INV11_WASM_TOOLS"


def find_tool() -> str | None:
    exe = os.environ.get(ENV) or shutil.which("wasm-tools")
    return exe if exe and os.path.isfile(exe) else None


def tool_version(exe: str) -> str:
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    return out.split()[1] if len(out.split()) > 1 else out


def run_tool(exe: str, path: str) -> tuple[bool, dict | None, str]:
    r = subprocess.run([exe, "component", "wit", path, "--json"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return False, None, r.stderr.strip()
    return True, json.loads(r.stdout), ""


# ---- neutral view: authoritative tool ---------------------------------------
def theirs_view(doc: dict[str, Any], root: str | None = None) -> dict[str, Any]:
    types = doc["types"]
    ifaces = doc["interfaces"]
    pkgs = doc["packages"]

    def iname(i: int) -> str:
        it = ifaces[i]
        if it.get("package") is None or it.get("name") is None:
            return f"<anon {i}>"
        return pkgs[it["package"]]["name"].split("@")[0] + "/" + it["name"]

    def owner(t: dict) -> str:
        o = t.get("owner") or {}
        if "interface" in o:
            return iname(o["interface"])
        if "world" in o:
            w = doc["worlds"][o["world"]]
            return pkgs[w["package"]]["name"].split("@")[0] + "/" + w["name"]
        return "?"

    def ty(x: Any, depth: int = 0) -> Any:
        if depth > 200:
            raise ValueError("type nesting too deep")
        if isinstance(x, str):
            return x
        t = types[x]
        k = t["kind"]
        if isinstance(k, dict) and "type" in k:
            return ty(k["type"], depth + 1)  # alias (incl. `use`) is transparent
        if t.get("name") is not None and (k == "resource" or next(iter(k)) in ("record", "variant", "enum", "flags")):
            return f"N:{owner(t)}#{t['name']}"
        if k == "resource":
            return f"N:{owner(t)}#?"
        (kind, v), = k.items()
        if kind == "list":
            return ["list", ty(v, depth + 1)]
        if kind == "option":
            return ["option", ty(v, depth + 1)]
        if kind == "result":
            return ["result", ty(v["ok"], depth + 1) if v["ok"] is not None else None,
                    ty(v["err"], depth + 1) if v["err"] is not None else None]
        if kind == "tuple":
            return ["tuple"] + [ty(i, depth + 1) for i in v["types"]]
        if kind == "handle":
            (m, r), = v.items()
            return [m, ty(r, depth + 1)]
        if kind in ("future", "stream"):
            return [kind, ty(v, depth + 1) if v is not None else None]
        return ["?", kind]

    def fn(f: dict) -> Any:
        res = f.get("results") or []
        if isinstance(res, list):
            result = ty(res[0]["type"]) if res else None
        else:
            result = ty(res) if res is not None else None
        return {"params": [[p["name"], ty(p["type"])] for p in f["params"]], "result": result}

    def tdef(t: dict) -> Any:
        k = t["kind"]
        if k == "resource":
            return ["resource"]
        (kind, v), = k.items()
        if kind == "record":
            return ["record"] + [[f["name"], ty(f["type"])] for f in v["fields"]]
        if kind == "variant":
            return ["variant"] + [[c["name"], ty(c["type"]) if c["type"] is not None else None] for c in v["cases"]]
        if kind == "enum":
            return ["enum"] + [c["name"] for c in v["cases"]]
        if kind == "flags":
            return ["flags"] + [c["name"] for c in v["flags"]]
        return None

    out: dict[str, Any] = {"interfaces": {}, "worlds": {}}
    for idx, it in enumerate(ifaces):
        if it.get("name") is None:
            continue
        name = iname(idx)
        defs = {}
        for tname, ti in it["types"].items():
            d = tdef(types[ti])
            if d is not None:
                defs[tname] = d
        out["interfaces"][name] = {"functions": {k: fn(v) for k, v in it["functions"].items()}, "types": defs}
    for w in doc["worlds"]:
        wname = pkgs[w["package"]]["name"].split("@")[0] + "/" + w["name"]
        view = {}
        for direction in ("imports", "exports"):
            items: dict[str, Any] = {}
            for key, v in w[direction].items():
                if "interface" in v:
                    iid = v["interface"]["id"]
                    if ifaces[iid].get("name") is None:
                        items[key] = {"inline": sorted(ifaces[iid]["functions"])}
                    else:
                        items[iname(iid)] = "interface"
                elif "function" in v:
                    items[key] = fn(v["function"])
                elif "type" in v:
                    continue
            view[direction] = items
        out["worlds"][wname] = view
    return out


# ---- neutral view: this implementation ----------------------------------------
def ours_view(res: Resolved) -> dict[str, Any]:
    def strip(i: str) -> str:
        from .resolve import unversioned
        return unversioned(i)

    def nominal(key: str) -> str:
        return "N:" + strip(key)

    def deref(key: str, n: int = 0) -> Any:
        d = res.types[key]
        if d["kind"] == "alias":
            return ty(d["target"])
        return nominal(key)

    def ty(t: Any) -> Any:
        if isinstance(t, str) or t is None:
            return t
        if set(t) == {"ref"}:
            return deref(t["ref"])
        if "list" in t:
            return ["list", ty(t["list"])]
        if "option" in t:
            return ["option", ty(t["option"])]
        if "result" in t:
            return ["result", ty(t["result"]["ok"]), ty(t["result"]["err"])]
        if "tuple" in t:
            return ["tuple"] + [ty(x) for x in t["tuple"]]
        for m in ("own", "borrow"):
            if m in t:
                return [m, deref(t[m])]
        for m in ("future", "stream"):
            if m in t:
                return [m, ty(t[m])]
        return ["?"]

    def fn(f: dict, self_res: str | None = None) -> Any:
        params = [[p[0], ty(p[1])] for p in f["params"]]
        result = ty(f["result"])
        if f["kind"] == "method":
            assert self_res is not None
            params = [["self", ["borrow", nominal(self_res)]]] + params
        if f["kind"] == "constructor" and result is None:
            assert self_res is not None
            result = ["own", nominal(self_res)]
        return {"params": params, "result": result}

    def tdef(d: dict) -> Any:
        k = d["kind"]
        if k == "record":
            return ["record"] + [[n, ty(t)] for n, t in d["fields"]]
        if k == "variant":
            return ["variant"] + [[n, ty(t)] for n, t in d["cases"]]
        if k in ("enum", "flags"):
            return [k] + list(d["cases"])
        if k == "resource":
            return ["resource"]
        return None

    out: dict[str, Any] = {"interfaces": {}, "worlds": {}}
    for iid, i in sorted(res.interfaces.items()):
        funcs = {k: fn(v) for k, v in i["functions"].items()}
        defs = {}
        for tname, key in i["scope"].items():
            d = res.types[key]
            # a `use`d name becomes a local alias in wasm-tools; aliases are transparent
            if key.startswith(iid + "#") and d["kind"] != "alias":
                defs[tname] = tdef(d)
            if key.startswith(iid + "#") and d["kind"] == "resource":
                for m, f in d["methods"].items():
                    label = {"constructor": f"[constructor]{tname}", "method": f"[method]{tname}.{m}",
                             "static": f"[static]{tname}.{m}"}[f["kind"]]
                    funcs[label] = fn(f, key)
        out["interfaces"][strip(iid)] = {"functions": funcs, "types": defs}
    for wid, w in sorted(res.worlds.items()):
        view = {}
        for direction in ("imports", "exports"):
            items: dict[str, Any] = {}
            for key, v in w[direction].items():
                if v["kind"] == "interface":
                    items[strip(v["ref"])] = "interface"
                elif v["kind"] == "func":
                    items[key] = fn(v["sig"])
                else:
                    items[key] = {"inline": sorted(v["functions"])}
            view[direction] = items
        out["worlds"][strip(wid)] = view
    return out


def compare_views(ours: dict, theirs: dict, path: str = "") -> list[str]:
    if isinstance(ours, dict) and isinstance(theirs, dict):
        out = []
        for k in sorted(set(ours) | set(theirs)):
            if k not in ours:
                out.append(f"{path}/{k}: only in reference")
            elif k not in theirs:
                out.append(f"{path}/{k}: only in ours")
            else:
                out.extend(compare_views(ours[k], theirs[k], f"{path}/{k}"))
        return out
    return [] if ours == theirs else [f"{path}: ours={json.dumps(ours)} reference={json.dumps(theirs)}"]


def differential(path: str, res_ok: bool, res: Resolved | None, exe: str) -> dict[str, Any]:
    ok, doc, err = run_tool(exe, path)
    row: dict[str, Any] = {"input": os.path.basename(path), "ours_accepts": res_ok, "reference_accepts": ok}
    if ok != res_ok:
        row.update(verdict="DIVERGENT", reason="accept/reject disagreement", reference_error=err[:400])
        return row
    if not ok:
        row.update(verdict="AGREE_REJECT")
        return row
    assert res is not None and doc is not None
    diffs = compare_views(ours_view(res), theirs_view(doc))
    # dependency packages appear in the reference output too; compare only what we resolved
    row.update(verdict="AGREE" if not diffs else "DIVERGENT", divergences=diffs[:50])
    return row


def pinned_ok(exe: str) -> bool:
    return tool_version(exe) == MATRIX["reference_toolchain"]["pinned"]
