"""M02 gate: pk_core must be importable AND pinned in lock/pk_core.lock.json."""
import json, pathlib, sys
lock = json.loads((pathlib.Path(__file__).resolve().parents[2] / "lock/pk_core.lock.json").read_text())
try:
    import pk_core  # noqa: F401
    importable = True
except ModuleNotFoundError:
    importable = False
pinned = all(lock.get(k) for k in ("version", "sha256", "source"))
print(json.dumps({"importable": importable, "pinned": pinned, "lock": lock}))
sys.exit(0 if importable and pinned else 1)
