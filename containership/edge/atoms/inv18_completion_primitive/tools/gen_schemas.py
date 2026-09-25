"""Regenerate schemas/*.json from wire.SCHEMAS (the single source of truth)."""
import json, pathlib, sys
pkg = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(pkg.parent))
wire = __import__(pkg.name + ".wire", fromlist=["SCHEMAS"])
out = pkg / "schemas"
out.mkdir(exist_ok=True)
for name, sch in wire.SCHEMAS.items():
    (out / (name.replace("/", "_v") + ".json")).write_text(json.dumps(sch, indent=1, sort_keys=True) + "\n")
    print("wrote", name)
