"""Verify SHA256SUMS.txt against the package tree (MC49-012)."""
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
bad = 0
for line in (root / "SHA256SUMS.txt").read_text().splitlines():
    digest, rel = line.split("  ", 1)
    p = root / rel
    if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
        print("MISMATCH", rel)
        bad += 1
print(f"{'OK' if not bad else 'FAIL'}: {bad} mismatches")
sys.exit(1 if bad else 0)
