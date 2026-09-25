"""Regenerate SHA256SUMS.txt over every shipped file (excluding caches and itself)."""
import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
lines = []
for p in sorted(root.rglob("*")):
    rel = p.relative_to(root).as_posix()
    if (p.is_file() and "__pycache__" not in rel and rel != "SHA256SUMS.txt"
            and not (rel.startswith("evidence/") and rel != "evidence/run_evidence.py")):
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
(root / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
print(len(lines), "files")
