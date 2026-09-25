"""Regenerate interfaces/schema-manifest.json (sha256 of every public schema). --check fails on drift."""
import hashlib, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
MAN = ROOT / "interfaces" / "schema-manifest.json"
def compute():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT / "schemas").iterdir())}
if __name__ == "__main__":
    man = json.loads(MAN.read_text())
    if "--check" in sys.argv:
        drift = {k for k in set(man["sha256"]) | set(compute()) if man["sha256"].get(k) != compute().get(k)}
        print("schema manifest OK" if not drift else f"schema drift: {sorted(drift)}")
        sys.exit(1 if drift else 0)
    man["sha256"] = compute(); MAN.write_text(json.dumps(man, indent=2) + "\n"); print("written", MAN)
