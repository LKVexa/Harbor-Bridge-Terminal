"""Verify every file against SHA256SUMS; report missing/extra/modified. Exit 1 on any difference."""
import hashlib, pathlib, sys
PKG = pathlib.Path(__file__).resolve().parents[1]
want = {}
for line in (PKG / "SHA256SUMS").read_text().splitlines():
    h, name = line.split("  ", 1); want[name] = h
have = {p.relative_to(PKG).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in PKG.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != "SHA256SUMS"}
mod = sorted(k for k in want if k in have and have[k] != want[k])
miss = sorted(set(want) - set(have)); extra = sorted(set(have) - set(want))
print(f"files {len(want)}  modified {len(mod)}  missing {len(miss)}  extra {len(extra)}")
for k in mod + miss + extra:
    print("  ", k)
sys.exit(1 if mod or miss or extra else 0)
