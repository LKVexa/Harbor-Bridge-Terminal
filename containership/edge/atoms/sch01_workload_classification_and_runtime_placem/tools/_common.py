from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent)); sys.path.insert(0, str(PKG / "tools"))
sys.dont_write_bytecode = True
def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p: Path, o) -> None: p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(o, indent=2, sort_keys=True) + "\n")
def files():
    skip = {"__pycache__", ".git"}
    return sorted(p for p in PKG.rglob("*") if p.is_file() and not skip & set(p.relative_to(PKG).parts)
                  and p.name != "RELEASE_SHA256SUMS.txt")
