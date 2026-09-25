"""M28/M29 - render two environments and print the effective-config diff for review."""
import argparse, json, pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.dont_write_bytecode = True
from inv60_wasm_application_fabric.fabric import config as cf
ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="src", required=True); ap.add_argument("--to", dest="dst", required=True)
a = ap.parse_args()
base = json.loads((PKG / "config/base.json").read_text())
r = {e: cf.render(base, (e, json.loads((PKG / "config/overlays" / f"{e}.json").read_text()))) for e in (a.src, a.dst)}
print(json.dumps({"from": a.src, "to": a.dst, "from_digest": cf.digest(r[a.src]), "to_digest": cf.digest(r[a.dst]),
                  "diff": cf.diff(r[a.src], r[a.dst])}, indent=1))
