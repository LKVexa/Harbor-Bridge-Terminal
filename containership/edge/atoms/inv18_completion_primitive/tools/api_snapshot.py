"""Public API + schema snapshot and undeclared-break check (C016, C027).

  python tools/api_snapshot.py --write   # record conformance/API_SNAPSHOT.json
  python tools/api_snapshot.py           # compare; exit 1 on undeclared change
"""
import inspect, json, pathlib, sys
pkg = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pkg.parent))
import importlib


def snapshot():
    m = importlib.import_module(pkg.name)
    api = {}
    for mod in ("future", "errors", "runtime", "wire", "config", "auth", "adapters", "retry"):
        mm = importlib.import_module(f"{pkg.name}.{mod}")
        for name, obj in sorted(vars(mm).items()):
            if name.startswith("_") or getattr(obj, "__module__", None) != mm.__name__:
                continue
            if inspect.isclass(obj):
                api[f"{mod}.{name}"] = sorted(n for n in vars(obj) if not n.startswith("_") or n == "__init__")
            elif inspect.isfunction(obj):
                api[f"{mod}.{name}"] = str(inspect.signature(obj))
    wire = importlib.import_module(f"{pkg.name}.wire")
    errors = importlib.import_module(f"{pkg.name}.errors")
    return {"version": m.__version__, "exports": sorted(m.__all__), "api": api,
            "schemas": {k: sorted(v["properties"]) for k, v in wire.SCHEMAS.items()},
            "required": {k: sorted(v.get("required", [])) for k, v in wire.SCHEMAS.items()},
            "error_codes": sorted(errors.CODES)}


def diff(old, new):
    removed, added = [], []
    for k in ("exports", "error_codes"):
        removed += [f"{k}:{x}" for x in old[k] if x not in new[k]]
        added += [f"{k}:{x}" for x in new[k] if x not in old[k]]
    for k, v in old["api"].items():
        if k not in new["api"]:
            removed.append(f"api:{k}")
        elif v != new["api"][k]:
            if isinstance(v, list) and set(v) <= set(new["api"][k]):
                added.append(f"api:{k}")
            else:
                removed.append(f"api:{k} changed")
    added += [f"api:{k}" for k in new["api"] if k not in old["api"]]
    for s, props in old["schemas"].items():
        if s not in new["schemas"] or set(props) - set(new["schemas"][s]) or set(new["required"].get(s, [])) - set(old["required"][s]):
            removed.append(f"schema:{s}")
    return removed, added


def check(old, new):
    removed, added = diff(old, new)
    ov, nv = [int(x) for x in old["version"].split(".")], [int(x) for x in new["version"].split(".")]
    problems = []
    if removed and nv[0] == ov[0]:
        problems.append(f"breaking change without major bump: {removed}")
    if added and nv[:2] == ov[:2] and not removed:
        problems.append(f"additions without minor bump: {added}")
    return problems


if __name__ == "__main__":
    snap_p = pkg / "conformance/API_SNAPSHOT.json"
    new = snapshot()
    if "--write" in sys.argv:
        snap_p.write_text(json.dumps(new, indent=1, sort_keys=True))
        print("snapshot written")
        sys.exit(0)
    probs = check(json.loads(snap_p.read_text()), new)
    print("\n".join(probs) or "API compatible with snapshot")
    sys.exit(1 if probs else 0)
