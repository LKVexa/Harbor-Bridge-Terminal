"""Write SHA256SUMS for the whole package (excluding itself and bytecode)."""
import hashlib, pathlib
PKG = pathlib.Path(__file__).resolve().parents[1]
lines = []
for p in sorted(PKG.rglob("*")):
    if p.is_file() and "__pycache__" not in p.parts and p.name != "SHA256SUMS":
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PKG).as_posix()}")
(PKG / "SHA256SUMS").write_text("\n".join(lines) + "\n")
print(len(lines), "files sealed")
