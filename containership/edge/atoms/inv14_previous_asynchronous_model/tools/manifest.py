"""Write/check MANIFEST.sha256 (relative paths, sorted) over every shipped file.
Excluded: the manifest itself, its signature, __pycache__/.pyc, evidence/ (run output
is hashed separately inside evidence/EVIDENCE_MANIFEST.sha256)."""
import hashlib, sys
import _path  # noqa
PKG = _path.PKG
EXCL = {"MANIFEST.sha256", "MANIFEST.sha256.sig.json"}


def entries():
    for p in sorted(PKG.rglob("*")):
        rel = p.relative_to(PKG).as_posix()
        if p.is_file() and rel not in EXCL and "__pycache__" not in p.parts and p.suffix != ".pyc" and not rel.startswith("evidence/"):
            yield f"{hashlib.sha256(p.read_bytes()).hexdigest()}  ./{rel}"


def main(check=False):
    txt = "\n".join(entries()) + "\n"
    m = PKG / "MANIFEST.sha256"
    if check:
        ok = m.exists() and m.read_text() == txt
        if not ok and m.exists():
            old, new = set(m.read_text().splitlines()), set(txt.splitlines())
            print("manifest mismatch:", sorted(old ^ new)[:10])
        return 0 if ok else 1
    m.write_text(txt); print(f"{txt.count(chr(10))} entries"); return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
